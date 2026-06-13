# Notas de voz (voice notes)

Una nota de voz es **otra forma de redactar un check-in**, no un canal nuevo. El
audio se transcribe **en el borde** (canal/API) y el texto resultante entra al
*mismo* flujo de extracción/check-in que un mensaje escrito, con el **mismo nivel
de confianza**: es una propuesta no confiable que el código determinista valida
antes de persistir nada. El núcleo de la conversación **nunca ve audio**.

```
audio (OGG/WebM/WAV/MP3)
      │  (borde: canal / API)
      ▼
  Transcriber.transcribe(VoiceClip) ─▶ Transcript(text, …)   ← texto NO confiable
      │
      ▼
  flujo de check-in existente (router → extracción → validación → persistencia)
```

## El puerto `Transcriber`

`src/lumi/ports/transcription.py` — depende solo de tipos stdlib, así que
importarlo nunca arrastra un modelo de voz.

```python
@dataclass(frozen=True)
class VoiceClip:
    data: bytes                      # audio crudo codificado (OGG/Opus, WAV, WebM…)
    mime: str = "audio/ogg"
    duration_s: float | None = None
    reference: str | None = None     # tag opaco para adapters de fixture (demo/tests)

@dataclass(frozen=True)
class Transcript:
    text: str                        # NO confiable: alimenta la extracción normal
    language: str = "es"
    confidence: float | None = None
    duration_s: float | None = None

class Transcriber(Protocol):
    def transcribe(self, clip: VoiceClip) -> Transcript: ...
```

`reference` lo usan solo los adapters de fixture para resolver un transcript
guionizado; los transcriptores reales lo ignoran y leen `data`. Nunca es un
nombre de cuidador ni de menor.

## Los 3 adapters

Todos detrás del puerto; intercambiarlos es una línea en `build_transcriber`.

| Adapter | Archivo | Uso | Dep |
|---|---|---|---|
| `CannedTranscriber` | `adapters/media/canned.py` | demo y tests rápidos; resuelve un transcript fijo por `reference`, nunca inspecciona `data` | ninguna |
| `AzureWhisperTranscriber` | `adapters/media/azure_whisper.py` | **motor real preferido**; STT vía Azure OpenAI Whisper | extra `[azure]` (`openai`, `azure-identity`) |
| `FasterWhisperTranscriber` | `adapters/media/faster_whisper.py` | fallback local opcional (CTranslate2, sin PyTorch) | extra `[voice]` (`faster-whisper`) |

### Selección — `build_transcriber()` (`api/bootstrap.py`)

Prioridad: **Azure → faster-whisper local → canned no-op**, y gateado por
`use_ai` para que tests y demos offline nunca construyan un cliente Azure.

```
disabled (use_ai=False) ─────────────────────────▶ CannedTranscriber({})   (no-op)
no disabled:
  Azure configurado (from_env OK) ───────────────▶ AzureWhisperTranscriber
  LUMI_VOICE_LOCAL=1 y [voice] instalado ────────▶ FasterWhisperTranscriber
  si no ──────────────────────────────────────────▶ CannedTranscriber({})   (no-op)
```

Los imports `openai`/`azure-identity`/`faster_whisper` son **perezosos** (dentro
de `__init__`/funciones), nunca a nivel de módulo: el núcleo de Lumi no importa
ninguna dep pesada de voz. Garantizado por `tests/lumi/test_boundaries.py`.

## Endpoints HTTP

Dos caminos distintos, a propósito:

### `POST /api/voice` — muestras guionizadas (stage-safe)

Las notas de muestra del demo son **fixtures sin audio**. El transcript se
resuelve **directo del fixture** (`voice_samples.py`), sin pasar por el motor →
los chips 🎤 del demo funcionan en escenario **con o sin** engine cableado.

```jsonc
// req:  { "id": "voz-mala-noche" }
// resp: { "transcript": "...", "duration": "0:09", "reply": "...", "snapshot": {…} }
```

### `POST /api/voice/upload` — audio real

Audio grabado de verdad (base64 JSON, sin `multipart`) → `Transcriber`
(Azure cuando hay deployment) → mismo flujo de check-in no confiable. **El audio
se transcribe en el borde y se descarta; nunca se persiste ni se loguea.**

```jsonc
// req:  { "audio_b64": "<base64>", "mime": "audio/webm", "duration_s": 6 }
// resp: { "transcript": "...", "duration": "0:06", "reply": "...", "snapshot": {…} }
// 422 si base64 inválido o vacío; transcript "" (200) si no hay engine cableado.
```

En el demo WhatsApp, el botón 🎤 graba con `MediaRecorder` y postea a este
endpoint (feature-detect: se oculta si el navegador no graba; fallback honesto
"configura Azure Whisper" si no hay motor).

## Gotcha: Whisper en Azure usa el **path clásico**, no `/openai/v1`

Whisper en Azure OpenAI **no** se sirve en el surface `/openai/v1` que usa el
extractor de chat (`gpt-4.1`) — pegarle ahí devuelve **`DeploymentNotFound`**. Se
sirve en el path clásico *deployment-scoped*:

```
POST {endpoint}/openai/deployments/{deployment}/audio/transcriptions?api-version=2024-06-01
```

Por eso `AzureWhisperTranscriber` usa el cliente **`AzureOpenAI`** (con
`api_version`), no el cliente `OpenAI` apuntado a `/openai/v1/`. El endpoint se
normaliza quitando un sufijo `/openai/v1` si viene (`azure_endpoint`).

Credenciales (igual que el extractor): Entra ID por defecto
(`DefaultAzureCredential` / managed identity) y `AZURE_OPENAI_API_KEY` como
fallback explícito. La key nunca se persiste ni loguea.

### Configuración (env)

```bash
AZURE_AI_ENDPOINT=https://<resource>.services.ai.azure.com/   # reutiliza el del extractor
AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT=whisper                    # deployment de transcripción
LUMI_VOICE_LANGUAGE=es                                        # idioma (default es)
# AZURE_OPENAI_TRANSCRIBE_API_VERSION=2024-06-01              # override opcional
# LUMI_VOICE_LOCAL=1                                          # usa faster-whisper en vez de Azure
```

El deployment `whisper` (001) hay que crearlo en el recurso (es distinto del de
chat). Modelos de transcripción disponibles en eastus2: `whisper`,
`gpt-4o-transcribe`, `gpt-4o-mini-transcribe`.

```bash
az cognitiveservices account deployment create \
  --name <resource> --resource-group <rg> \
  --deployment-name whisper --model-name whisper --model-version 001 \
  --model-format OpenAI --sku-name Standard --sku-capacity 1
```

## Tests

- `tests/lumi/media/test_transcription.py` — puerto + adapter canned (rápido).
- `tests/lumi/media/test_azure_whisper.py` — adapter Azure con **cliente fake**
  (sin red): sube audio, reenvía idioma, deriva sufijo por MIME, `from_env`
  exige endpoint+deployment, normaliza `/openai/v1`, no almacena la key.
- `tests/lumi/media/test_faster_whisper_slow.py` — adapter local (slow; salta sin
  el modelo/clip).
- `tests/lumi/test_voice_api.py` — endpoints: muestra→fixture, upload con
  transcriber inyectado, validación base64, comportamiento sin engine.
- `tests/lumi/test_boundaries.py` — el núcleo no importa deps pesadas de voz.

Pendiente (issue **lumi-bdc**): clip de voz es-PE *committeado* para que el slow
test deje de saltarse y valide calidad real.

## Deploy (estado de esta entrega)

El demo está desplegado en **Azure App Service** (Linux container):
`https://lumi-demo-cg65uw.azurewebsites.net` — HTTPS (necesario para el micrófono),
imagen mínima (solo deps de Lumi, **sin TensorFlow**) desde ACR.

Notas de decisión:

- **No es Azure Container Apps** (la opción preferida): el provider
  `Microsoft.App` está **sin registrar** en la suscripción y registrarlo requiere
  permiso a nivel suscripción que la cuenta (rol **Contributor** en el RG) no
  tiene. App Service (`Microsoft.Web`, ya registrado) es el equivalente viable
  sin admin. Si un admin registra `Microsoft.App` + `Microsoft.OperationalInsights`,
  se puede migrar a Container Apps (scale-to-zero).
- **Auth por API key como *app setting* (encriptado), no managed identity.** La
  managed identity necesitaría un role assignment ("Cognitive Services OpenAI
  User") sobre el recurso de IA, y **Contributor no puede crear role assignments**.
  La key vive como setting de App Service (no en el repo), y el pull del ACR usa
  credenciales de admin del registro (mismo motivo). Migrar a managed identity es
  un follow-up cuando haya permisos de RBAC.
- La imagen instala solo `[web]`+`[azure]` (FastAPI/uvicorn/openai/azure-identity),
  **no** las deps base del experimento acústico (TensorFlow, sounddevice…), porque
  el paquete `lumi` está aislado de `dermatomicos_bago`.
