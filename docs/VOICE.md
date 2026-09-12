# Voice Control: a PiCar you can talk to

Hold a button on your phone, say *"what can you see?"*, and the car aims its
camera, looks, and answers out loud. Say *"drive forward a bit"* and it checks
the way is clear first.

Speech recognition runs in your **browser**, not on the Pi. Your phone is
already an excellent microphone with an excellent recogniser built in, so the
default setup needs no extra hardware at all — no USB mic, no wake-word
engine, no audio configuration. The recognised text is POSTed to the Pi,
Claude decides what the car should do, and the reply comes back out of the
car's own speaker.

---

## How it fits together

```
 Your phone                        Raspberry Pi                     Anthropic
┌──────────────┐   text command   ┌──────────────────────┐        ┌──────────┐
│ Web Speech   │ ───────────────► │ POST /api/voice/     │ ─────► │  Claude  │
│ recognition  │                  │        command       │        │          │
│              │ ◄─────────────── │                      │ ◄───── │ picks a  │
└──────────────┘  reply + actions │  VoiceAgent loop     │  tool  │   tool   │
                                  │    ├─ drive / turn   │  calls └──────────┘
                                  │    ├─ look / see ────┼──► camera frame
                                  │    └─ stop / state   │      (sent as an image)
                                  │           ▼          │
                                  │  RobotSkills (clamps)│
                                  │           ▼          │
                                  │  motors / servos     │
                                  │           ▼          │
                                  │  espeak-ng ──► speaker
                                  └──────────────────────┘
```

The agent loop is a normal Claude tool-use loop: Claude gets the robot's
capabilities as tools, calls them, sees the results (including camera frames
as images), and finishes with a sentence to say out loud.

---

## Setup

### 1. Get an API key

Create one at [console.anthropic.com](https://console.anthropic.com/settings/keys).

### 2. Install the dependencies on the Pi

```bash
cd ~/picar-x
uv pip install -r requirements.txt          # now includes anthropic
sudo apt-get install -y espeak-ng           # so the car speaks for itself
```

`espeak-ng` is optional. Without it the reply text comes back to the browser
and your phone speaks it instead — which works, but the car talking with its
own voice is most of the fun.

### 3. Set the key and start the server

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export PICAR_AUTH_USERNAME="pick-a-username"     # strongly recommended, see Security
export PICAR_AUTH_PASSWORD="pick-a-strong-password"
./start.sh
```

For the systemd service, put the key in the unit rather than a shell profile:

```ini
# /etc/systemd/system/picar.service
[Service]
Environment="ANTHROPIC_API_KEY=sk-ant-..."
Environment="PICAR_AUTH_USERNAME=picar"
Environment="PICAR_AUTH_PASSWORD=..."
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart picar
```

Check it took:

```bash
curl -u picar:... http://<pi-ip>:5000/api/voice/status
```

`"available": true` means you're ready.

### 4. Open the web interface and press the microphone

The **Talk to the Car** panel sits above the movement controls.

---

## The microphone needs a secure connection

This is the one setup wrinkle worth knowing about in advance.

Browsers only allow microphone access in a *secure context*. Over plain
`http://192.168.1.204:5000` the microphone is blocked — usually silently. The
page detects this and tells you, and the typed-command box keeps working, but
for actual voice you need one of these:

**Option A — tell Chrome to trust the Pi (easiest, desktop Chrome/Edge)**

Open `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, add
`http://192.168.1.204:5000`, and relaunch. Fine for a robot on your own LAN;
don't do it for origins you don't control.

**Option B — an SSH tunnel (no browser settings to change)**

```bash
ssh -L 5000:localhost:5000 pi@192.168.1.204
```

Then use `http://localhost:5000`, which browsers already treat as secure.

**Option C — HTTPS with a self-signed certificate (works on phones)**

The only option that gives you voice control from a phone on the LAN.

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -keyout picar-key.pem -out picar-cert.pem \
  -subj "/CN=picar.local" \
  -addext "subjectAltName=IP:192.168.1.204"
```

Put a TLS terminator (Caddy, nginx, or `waitress` behind one) in front of port
5000. You'll have to accept the certificate warning once per device.

---

## Using it

| Control | What it does |
|---|---|
| **🎤 Tap to talk** | Listens for one command, then acts on it. |
| **Hands-free** | Keeps listening; acts only on utterances that start with "Claude". |
| **■ STOP** | Emergency stop. Never reaches the model — see below. |
| **Clear chat** | Forgets the conversation so far. |
| **Text box** | Type a command. Always available, even without a microphone. |

Things worth trying:

- *"What can you see?"*
- *"Look down and tell me if the floor is clear."*
- *"Drive forward a little, then tell me what's in front of you."*
- *"Turn left and look around."*
- *"Is there anything I could bump into?"*

Hands-free mode requires the wake word so that a conversation happening in the
room doesn't drive the car across the floor. "Cloud" and "clod" are accepted
too, because recognisers mishear "Claude" constantly.

---

## Safety

An LLM steering a real vehicle in someone's home needs limits that don't
depend on the model behaving well. There are three layers, and only the third
one relies on Claude's judgement.

**1. The movement envelope (`config/config.py`)** — enforced in code, in
`picar/voice/skills.py`. Nothing Claude can say widens it.

| Setting | Default | What it caps |
|---|---|---|
| `PICAR_VOICE_MAX_SPEED` | `45` | Top speed the agent may use (manual control still allows 100) |
| `PICAR_VOICE_MAX_MOVE_SECONDS` | `2.0` | Longest single movement |
| `PICAR_VOICE_MAX_TOTAL_MOVE_SECONDS` | `8.0` | Total movement per spoken command |
| `PICAR_VOICE_MAX_TOOL_CALLS` | `12` | Actions per spoken command |

Every movement is **self-terminating**: there is no "start driving" primitive,
so a crashed process or a dropped connection cannot leave the car rolling. The
motor watchdog already in `MotorController` is the backstop underneath that.

**2. The stop path** — the STOP button and the spoken word "stop" both go
straight to `/api/voice/stop`, which sets an abort flag and cuts the motors.
It does not wait for the model, the network, or the current movement: drives
in progress check the flag every 50 ms. Stopping the car never depends on an
API call succeeding.

**3. The system prompt** — Claude is told to look before driving anywhere it
hasn't seen, to refuse to drive toward stairs, drops, water, pets or cables,
and to treat a view too dark to judge as unsafe. This layer is the one that
handles cases the first two can't anticipate, and it is the one you should
trust least. Keep the car in sight.

### Security

The voice endpoints inherit the app's authentication settings, which are
**off by default**. With an API key configured, an open server means anyone
who can reach the Pi can drive your car *and* spend your Anthropic credits.
Set `PICAR_AUTH_USERNAME`/`PICAR_AUTH_PASSWORD` — the server logs a warning at
startup if you don't. Don't port-forward this to the internet.

---

## Configuration

All optional; the defaults are what most people want.

| Variable | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Voice control is off without it. |
| `PICAR_VOICE_ENABLED` | `1` | Set `0` to disable even with a key present. |
| `PICAR_VOICE_MODEL` | `claude-opus-5` | Any current Claude model. |
| `PICAR_VOICE_EFFORT` | `low` | `low` keeps replies quick, which matters for speech. Raise for genuinely multi-step tasks; `none` omits the thinking/effort parameters entirely. |
| `PICAR_VOICE_HISTORY_TURNS` | `12` | Conversation turns kept. |
| `PICAR_VOICE_TTS_ENABLED` | `1` | `0` to always speak through the browser. |
| `PICAR_VOICE_TTS_VOICE` | `en-us` | Any espeak-ng voice (`espeak-ng --voices`). |
| `PICAR_VOICE_TTS_WPM` | `165` | Speaking rate. |

Cost is modest: a typical command is one or two API calls, and the system
prompt and tool definitions are cached across calls. Commands that involve
looking cost more, since each photo is an image input.

---

## Optional: a microphone on the car itself

To cut the phone out of the loop entirely, plug a USB microphone into the Pi
and install local transcription:

```bash
uv pip install faster-whisper
```

Then POST audio to `/api/voice/audio` instead of text:

```bash
arecord -d 4 -f cd -t wav /tmp/cmd.wav
curl -u picar:... -F "audio=@/tmp/cmd.wav" http://<pi-ip>:5000/api/voice/audio
```

Expect one to three seconds of transcription on a Pi 4 with the default
`base.en` model. `PICAR_VOICE_STT_MODEL=tiny.en` is roughly twice as fast and
noticeably worse with names. The model loads on first use and stays resident
(~150 MB), so installs that never use this path pay nothing.

---

## API reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/voice/status` | GET | Whether voice control is available, busy, and its limits |
| `/api/voice/command` | POST | `{"text": "..."}` — run a command, returns reply and actions |
| `/api/voice/audio` | POST | Multipart `audio` file — transcribe on the Pi, then run it |
| `/api/voice/stop` | POST | Emergency stop. Never reaches the model |
| `/api/voice/reset` | POST | Forget the conversation |
| `/api/voice/transcript` | GET | The conversation so far |

A successful command returns:

```json
{
  "status": "success",
  "transcript": "drive forward a bit",
  "reply": "Moved forward a little. There's a chair leg ahead.",
  "actions": [
    {"name": "see", "detail": "captured a 20141 byte frame", "aborted": false},
    {"name": "drive", "detail": "forward at 30% for 1.0s", "aborted": false}
  ],
  "aborted": false,
  "tool_calls": 2,
  "hit_tool_limit": false,
  "spoken_on_pi": true,
  "state": {"moving": false, "steering_angle": 0, "...": "..."}
}
```

---

## Troubleshooting

**`"available": false` in `/api/voice/status`** — the key isn't reaching the
process. A key exported in your shell isn't visible to a systemd service; put
it in the unit file. Check with
`sudo systemctl show picar -p Environment`.

**The microphone button is disabled** — you're on plain HTTP. See *the
microphone needs a secure connection* above. The text box works meanwhile.

**The car doesn't speak, but replies appear on screen** — `espeak-ng` isn't
installed, or the Robot Hat's amplifier is off. Test the audio path directly:

```bash
espeak-ng "hello from the car"
```

**Replies are slow** — most of the latency is the model. `PICAR_VOICE_EFFORT`
is already `low`; commands involving `see` are slower because a photo is
uploaded. `PICAR_VOICE_MODEL=claude-haiku-4-5` trades noticeable judgement for
speed — a poor trade for the safety-relevant "is it clear ahead?" calls.

**It says it can't see anything real** — the camera is in simulation mode, so
it's being handed a blank placeholder and is correctly refusing to make
something up. Check `rpicam-still --list-cameras` and that `picamera2` is
visible to the venv (`uv venv --system-site-packages`).

**It refuses to drive** — usually correct behaviour. Ask *"what can you
see?"* to find out why. If the view is dark, add light: it's told to treat
"too dark to judge" as unsafe.
