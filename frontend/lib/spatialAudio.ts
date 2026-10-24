"use client";

class SpatialAudioEngine {
  private ctx: AudioContext | null = null;
  private panner: PannerNode | null = null;

  private initContext() {
    if (typeof window === "undefined") return;
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  }

  /**
   * Play a spatialized acoustic chime/ping when an object is detected.
   * @param panX Horizontal pan (-1.0 far left to +1.0 far right)
   * @param freq Tone frequency in Hz (default: 880Hz / A5)
   */
  public playSpatialPing(panX: number = 0, freq: number = 880) {
    try {
      this.initContext();
      if (!this.ctx) return;

      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const panner = this.ctx.createPanner();

      panner.panningModel = "HRTF";
      panner.distanceModel = "inverse";
      panner.positionX.setValueAtTime(Math.max(-1, Math.min(1, panX)), this.ctx.currentTime);
      panner.positionY.setValueAtTime(0, this.ctx.currentTime);
      panner.positionZ.setValueAtTime(-1, this.ctx.currentTime);

      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(freq * 1.5, this.ctx.currentTime + 0.08);

      gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.18);

      osc.connect(gain);
      gain.connect(panner);
      panner.connect(this.ctx.destination);

      osc.start();
      osc.stop(this.ctx.currentTime + 0.2);
    } catch (e) {
      console.debug("Spatial ping suppressed:", e);
    }
  }

  /**
   * Play Base64 MP3 speech positioned in 3D audio space.
   * @param audioBase64 Data URI or raw base64 MP3
   * @param panX Horizontal audio pan (-1.0 to 1.0)
   */
  public async playSpatialSpeech(audioBase64: string, panX: number = 0): Promise<void> {
    try {
      this.initContext();
      if (!this.ctx) return;

      let b64 = audioBase64;
      if (b64.includes(",")) {
        b64 = b64.split(",", 2)[1];
      }

      const binaryStr = window.atob(b64);
      const len = binaryStr.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }

      const audioBuffer = await this.ctx.decodeAudioData(bytes.buffer);
      const source = this.ctx.createBufferSource();
      const panner = this.ctx.createPanner();

      panner.panningModel = "HRTF";
      panner.distanceModel = "inverse";
      panner.positionX.setValueAtTime(Math.max(-1, Math.min(1, panX)), this.ctx.currentTime);
      panner.positionY.setValueAtTime(0, this.ctx.currentTime);
      panner.positionZ.setValueAtTime(-1, this.ctx.currentTime);

      source.buffer = audioBuffer;
      source.connect(panner);
      panner.connect(this.ctx.destination);
      source.start(0);
    } catch (e) {
      console.debug("Spatial speech playback fallback:", e);
    }
  }
}

export const spatialAudio = new SpatialAudioEngine();
