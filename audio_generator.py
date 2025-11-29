"""
Audio Generator Module
Handles audio generation, metronome creation, and audio mixing
"""

import numpy as np
from pydub import AudioSegment
from pathlib import Path


class AudioGenerator:
    """Audio generator for workout pacer"""

    def __init__(self, sample_rate=44100):
        """
        Initialize audio generator

        Args:
            sample_rate: Sample rate, default 44100 Hz
        """
        self.sample_rate = sample_rate

    def _generate_click_samples(self, frequency=800, duration=0.05, volume=0.5):
        """
        Generate click sound as numpy array

        Args:
            frequency: Frequency (Hz)
            duration: Duration (seconds)
            volume: Volume (0-1)

        Returns:
            numpy array of samples
        """
        num_samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, num_samples, dtype=np.float32)
        
        # Generate sine wave
        samples = np.sin(2 * np.pi * frequency * t) * volume
        
        # Apply fade in/out (5ms each) to avoid clicks
        fade_samples = int(0.005 * self.sample_rate)
        if fade_samples > 0 and len(samples) > fade_samples * 2:
            # Fade in
            samples[:fade_samples] *= np.linspace(0, 1, fade_samples)
            # Fade out
            samples[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        return samples

    def _numpy_to_audio(self, samples):
        """
        Convert numpy array to AudioSegment

        Args:
            samples: numpy array of float samples (-1 to 1)

        Returns:
            AudioSegment
        """
        # Normalize and convert to int16
        samples = np.clip(samples, -1, 1)
        samples_int16 = (samples * 32767).astype(np.int16)
        
        # Create AudioSegment
        audio = AudioSegment(
            samples_int16.tobytes(),
            frame_rate=self.sample_rate,
            sample_width=2,  # 16-bit = 2 bytes
            channels=1
        )
        return audio

    def generate_metronome(self, bpm, beats_per_measure, duration_seconds,
                          click_frequency=800, accent_frequency=1200,
                          click_duration=0.05, volume=0.5, accent_first=True):
        """
        Generate metronome audio using fast numpy operations

        Args:
            bpm: Beats per minute
            beats_per_measure: Beats per measure (for accent)
            duration_seconds: Total duration (seconds)
            click_frequency: Normal beat frequency (Hz)
            accent_frequency: Accent beat frequency (Hz)
            click_duration: Click duration (seconds)
            volume: Volume (0-1)
            accent_first: Whether first beat is accented

        Returns:
            AudioSegment: Metronome audio
        """
        total_samples = int(duration_seconds * self.sample_rate)
        beat_interval_samples = int((60 / bpm) * self.sample_rate)
        
        # Calculate total beats
        total_beats = int(duration_seconds * bpm / 60)
        print(f"    Generating {total_beats} beats using optimized numpy...")
        
        # Generate click samples (once each)
        normal_click = self._generate_click_samples(click_frequency, click_duration, volume)
        accent_click = self._generate_click_samples(accent_frequency, click_duration, volume)
        click_len = len(normal_click)
        
        # Create silent base array
        samples = np.zeros(total_samples, dtype=np.float32)
        
        # Place clicks at beat positions (fast numpy operations)
        position = 0
        beat_count = 0
        
        while position + click_len < total_samples:
            # Choose click type (accent or normal)
            if accent_first and beat_count % beats_per_measure == 0:
                click = accent_click
            else:
                click = normal_click
            
            # Place click at position (numpy is O(1) for this)
            samples[position:position + click_len] += click
            
            position += beat_interval_samples
            beat_count += 1
        
        print(f"    ✓ Generated {beat_count} beats")
        
        # Convert to AudioSegment
        return self._numpy_to_audio(samples)

    def mix_audio_with_voice(self, base_audio, voice_files_map,
                           announcements, voice_volume=0.8):
        """
        Mix voice announcements into base audio

        Args:
            base_audio: Base audio (AudioSegment), can be metronome or silence
            voice_files_map: {text: file_path} dictionary
            announcements: List of announcements, each with 'time' and 'text'
            voice_volume: Voice volume (0-1)

        Returns:
            AudioSegment: Mixed audio
        """
        result = base_audio
        total = len(announcements)
        print(f"    Mixing {total} voice announcements...")

        for idx, announcement in enumerate(announcements, 1):
            if idx % 20 == 0:
                print(f"    Progress: {idx}/{total} ({idx/total*100:.1f}%)")

            time_ms = int(announcement['time'] * 1000)
            text = announcement.get('text', '')

            if text and text in voice_files_map:
                voice_file = voice_files_map[text]
                voice_audio = AudioSegment.from_mp3(voice_file)
                voice_audio = voice_audio - (100 * (1 - voice_volume))
                result = result.overlay(voice_audio, position=time_ms)

        print(f"    ✓ Mixed {total} announcements")
        return result

    def export_audio(self, audio, output_path, format="mp3"):
        """
        Export audio file

        Args:
            audio: AudioSegment object
            output_path: Output file path
            format: Output format (mp3 or wav)

        Returns:
            Path: Output file path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio.export(output_path, format=format)
        return output_path
