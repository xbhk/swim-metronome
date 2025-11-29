"""
TTS Service Module
Supports Edge TTS (default, free) and OpenAI TTS (optional, paid)
"""

import os
import asyncio
from pathlib import Path
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed


class BaseTTSService(ABC):
    """Base class for TTS services"""

    @abstractmethod
    def generate_speech(self, text, output_path, **kwargs):
        """Generate speech from text"""
        pass

    def generate_multiple_speeches(self, texts, output_dir, max_workers=10, **kwargs):
        """
        Generate multiple speech files concurrently

        Args:
            texts: List of texts to convert
            output_dir: Output directory
            max_workers: Max concurrent workers
            **kwargs: Additional arguments for generate_speech

        Returns:
            dict: {text: file_path} mapping
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        result = {}

        def generate_single(index_text):
            i, text = index_text
            filename = f"voice_{i:04d}.mp3"
            output_path = output_dir / filename
            try:
                self.generate_speech(text, output_path, **kwargs)
                return (text, output_path, None)
            except Exception as e:
                return (text, None, str(e))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(generate_single, (i, text)): text
                      for i, text in enumerate(texts)}

            completed = 0
            total = len(texts)

            for future in as_completed(futures):
                text, output_path, error = future.result()
                completed += 1

                if error:
                    print(f"✗ [{completed}/{total}] Failed: {text} - {error}")
                    raise RuntimeError(f"TTS generation failed: {text}")
                else:
                    result[text] = output_path
                    print(f"✓ [{completed}/{total}] {text}")

        return result


class EdgeTTSService(BaseTTSService):
    """
    Edge TTS Service - Free, no API key required
    Works in mainland China
    """

    # Default voices
    DEFAULT_VOICES = {
        "en": "en-US-AriaNeural",
        "zh": "zh-CN-XiaozhenNeural",
    }

    def __init__(self, voice=None, rate="+0%"):
        """
        Initialize Edge TTS service

        Args:
            voice: Voice name (e.g., "zh-CN-XiaozhenNeural", "en-US-AriaNeural")
            rate: Speech rate (e.g., "+10%", "-5%")
        """
        self.voice = voice
        self.rate = rate

    def _get_voice(self, text):
        """Auto-detect language and return appropriate voice"""
        if self.voice:
            return self.voice
        
        # Simple detection: if contains Chinese characters, use Chinese voice
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
        return self.DEFAULT_VOICES["zh"] if has_chinese else self.DEFAULT_VOICES["en"]

    def generate_speech(self, text, output_path, voice=None, rate=None):
        """
        Generate speech using Edge TTS

        Args:
            text: Text to convert
            output_path: Output file path
            voice: Override voice
            rate: Override speech rate
        """
        import edge_tts

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice = voice or self._get_voice(text)
        rate = rate or self.rate

        async def _generate():
            tts = edge_tts.Communicate(text, voice=voice, rate=rate)
            await tts.save(str(output_path))

        asyncio.run(_generate())
        return output_path


class OpenAITTSService(BaseTTSService):
    """
    OpenAI TTS Service - Premium quality, requires API key
    May not work in mainland China without proxy
    """

    def __init__(self, api_key=None, base_url=None, voice="nova", model="tts-1"):
        """
        Initialize OpenAI TTS service

        Args:
            api_key: OpenAI API Key (or set OPENAI_API_KEY env var)
            base_url: OpenAI API Base URL (or set OPENAI_BASE_URL env var)
            voice: Voice model (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (tts-1 or tts-1-hd)
        """
        from openai import OpenAI

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.voice = voice
        self.model = model

        if not self.api_key:
            raise ValueError(
                "OpenAI API Key required. Set OPENAI_API_KEY env var or pass api_key parameter."
            )

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)

    def generate_speech(self, text, output_path, voice=None, model=None):
        """
        Generate speech using OpenAI TTS

        Args:
            text: Text to convert
            output_path: Output file path
            voice: Override voice
            model: Override model
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice = voice or self.voice
        model = model or self.model

        try:
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            response.stream_to_file(str(output_path))
            return output_path

        except Exception as e:
            raise RuntimeError(f"OpenAI TTS failed: {str(e)}")


def get_tts_service(provider="edge", **kwargs):
    """
    Factory function to get TTS service

    Args:
        provider: "edge" (default, free) or "openai" (premium, paid)
        **kwargs: Provider-specific arguments

    Returns:
        TTS service instance
    """
    if provider == "edge":
        return EdgeTTSService(**kwargs)
    elif provider == "openai":
        return OpenAITTSService(**kwargs)
    else:
        raise ValueError(f"Unknown TTS provider: {provider}. Use 'edge' or 'openai'.")


# Backward compatibility
TTSService = OpenAITTSService


def test_tts_service():
    """Test TTS service"""
    print("Testing Edge TTS (default)...")
    
    tts = get_tts_service("edge")
    
    test_output = Path("output/test_edge_tts_service.mp3")
    tts.generate_speech("Testing Edge TTS", test_output)
    
    print(f"✓ Edge TTS test passed!")
    print(f"  File: {test_output}")
    print(f"  Size: {test_output.stat().st_size} bytes")


if __name__ == "__main__":
    test_tts_service()
