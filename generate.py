#!/usr/bin/env python3
"""
Workout Pacer Generator
Generate audio with voice announcements to help maintain steady pace
"""

import yaml
from pathlib import Path
from pydub import AudioSegment

from tts_service import get_tts_service
from audio_generator import AudioGenerator


# Internal defaults (hidden from user config)
DEFAULTS = {
    'warmup_seconds': 15,
    'metronome_enabled': False,
    'metronome_bpm': 55,
    'click_frequency': 800,
    'accent_frequency': 1200,
    'click_duration': 0.05,
    'beats_per_measure': 4,
    'sample_rate': 44100,
    'format': 'mp3',
    'voice_volume': 1.0,
    'output_filename': 'workout_pacer.mp3',
}


def load_config(config_path="config.yaml"):
    """Load configuration file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_time(time_str):
    """
    Parse time string like "2:00" to seconds

    Args:
        time_str: Time string like "2:00" or "1:45"

    Returns:
        int: Total seconds
    """
    if ':' in str(time_str):
        parts = str(time_str).split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes * 60 + seconds
    else:
        return int(time_str)


def process_config(config):
    """
    Process and validate config, apply defaults

    Required fields:
        - target_time: "2:00" (time to cover per_meters)
        - per_meters: 100 (reference distance)
        - total_distance: 1000 (total workout distance)
        - announce_every: 25 (announcement interval)
    """
    # Validate required fields
    required = ['target_time', 'per_meters', 'total_distance', 'announce_every']
    for field in required:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")

    # Parse target_time to seconds
    config['target_time_seconds'] = parse_time(config['target_time'])

    # Calculate speed (seconds per meter)
    config['seconds_per_meter'] = config['target_time_seconds'] / config['per_meters']

    # Calculate total workout duration
    workout_duration = config['total_distance'] * config['seconds_per_meter']
    config['workout_duration'] = int(workout_duration)

    # Apply defaults for optional fields
    config['warmup_seconds'] = config.get('warmup_seconds', DEFAULTS['warmup_seconds'])

    # Metronome defaults
    metronome = config.get('metronome', {})
    config['metronome'] = {
        'enabled': metronome.get('enabled', DEFAULTS['metronome_enabled']),
        'bpm': metronome.get('bpm', DEFAULTS['metronome_bpm']),
        'click_frequency': DEFAULTS['click_frequency'],
        'accent_frequency': DEFAULTS['accent_frequency'],
        'click_duration': DEFAULTS['click_duration'],
        'beats_per_measure': DEFAULTS['beats_per_measure'],
        'volume': 1.0,
    }

    # Voice defaults
    voice = config.get('voice', {})
    config['voice'] = {
        'language': voice.get('language', 'en'),
        'volume': DEFAULTS['voice_volume'],
    }

    # TTS defaults
    tts = config.get('tts', {})
    config['tts'] = {
        'provider': tts.get('provider', 'edge'),
        'edge': tts.get('edge', {
            'voice_zh': 'zh-CN-XiaoyuMultilingualNeural',
            'voice_en': 'en-US-AriaNeural',
        }),
        'openai': tts.get('openai', {}),
    }

    # Output defaults
    output = config.get('output', {})
    config['output'] = {
        'filename': output.get('filename', DEFAULTS['output_filename']),
        'format': DEFAULTS['format'],
        'sample_rate': DEFAULTS['sample_rate'],
    }

    # Total duration including warmup
    config['total_duration'] = config['warmup_seconds'] + config['workout_duration']

    return config


def get_tts_from_config(config):
    """Create TTS service based on config"""
    tts_config = config['tts']
    provider = tts_config.get('provider', 'edge')
    language = config['voice'].get('language', 'en')

    if provider == 'edge':
        edge_config = tts_config.get('edge', {})
        voice = edge_config.get('voice_zh') if language == 'zh' else edge_config.get('voice_en')
        return get_tts_service(provider='edge', voice=voice)
    elif provider == 'openai':
        openai_config = tts_config.get('openai', {})
        return get_tts_service(
            provider='openai',
            api_key=openai_config.get('api_key') or None,
            base_url=openai_config.get('base_url') or None,
        )
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def calculate_announcements(config):
    """
    Calculate all announcement times and texts

    Returns:
        list: [(time_seconds, text), ...]
    """
    announcements = []
    all_texts = set()
    language = config['voice'].get('language', 'en')
    warmup = config['warmup_seconds']

    # 1. Warmup phase announcements
    if warmup > 0:
        # Introduction at the very beginning
        if language == 'zh':
            intro_text = "现在是准备阶段，请做好准备"
        else:
            intro_text = "Get ready, workout starting soon"
        announcements.append({'time': 0, 'text': intro_text})
        all_texts.add(intro_text)

        # Full countdown: 10, 9, 8, 7, 6, 5, 4, 3, 2, 1
        # Countdown ends at warmup time, so starts at (warmup - 10)
        countdown_duration = min(10, warmup - 3)  # Leave 3 sec for intro
        
        # Chinese number mapping for TTS (Edge TTS struggles with single digits)
        chinese_numbers = {
            1: '一', 2: '二', 3: '三', 4: '四', 5: '五',
            6: '六', 7: '七', 8: '八', 9: '九', 10: '十'
        }
        
        for i in range(countdown_duration, 0, -1):
            actual_time = warmup - i
            text = chinese_numbers[i] if language == 'zh' else str(i)
            announcements.append({'time': actual_time, 'text': text})
            all_texts.add(text)

        # "Go!" at warmup end - more encouraging
        if language == 'zh':
            go_text = "开始！保持节奏，加油！"
        else:
            go_text = "Go! Keep the pace, let's go!"
        announcements.append({'time': warmup, 'text': go_text})
        all_texts.add(go_text)

    # 2. Distance announcements during workout
    announce_every = config['announce_every']
    seconds_per_meter = config['seconds_per_meter']
    total_distance = config['total_distance']

    distance = announce_every
    while distance <= total_distance:
        # Time when user should reach this distance
        time_at_distance = distance * seconds_per_meter + warmup

        # Only add if within total duration
        if time_at_distance < config['total_duration']:
            if language == 'zh':
                text = f"{distance}米"
            else:
                text = f"{distance} meters"

            announcements.append({
                'time': time_at_distance,
                'text': text,
                'distance': distance
            })
            all_texts.add(text)

        distance += announce_every

    # Sort by time
    announcements.sort(key=lambda x: x['time'])

    return announcements, list(all_texts)


def main():
    """Main program"""
    print("=" * 60)
    print("Workout Pacer Generator")
    print("=" * 60)

    # 1. Load config
    print("\n[1/6] Loading configuration...")
    config = load_config()
    config = process_config(config)

    target_time = config['target_time']
    per_meters = config['per_meters']
    total_distance = config['total_distance']
    announce_every = config['announce_every']
    warmup = config['warmup_seconds']
    workout_duration = config['workout_duration']
    total_duration = config['total_duration']

    print(f"  ✓ Configuration loaded")
    print(f"    - Target: {target_time} per {per_meters}m")
    print(f"    - Total distance: {total_distance}m")
    print(f"    - Announce every: {announce_every}m")
    print(f"    - Warmup: {warmup}sec")
    print(f"    - Workout duration: {workout_duration//60}min {workout_duration%60}sec")
    print(f"    - Total duration: {total_duration//60}min {total_duration%60}sec")

    # 2. Initialize audio generator
    print("\n[2/6] Initializing audio generator...")
    audio_gen = AudioGenerator(sample_rate=config['output']['sample_rate'])
    print("  ✓ Audio generator initialized")

    # 3. Generate base audio (metronome or silence)
    print("\n[3/6] Generating base audio...")
    if config['metronome']['enabled']:
        print(f"    - Metronome: {config['metronome']['bpm']} BPM")
        base_audio = audio_gen.generate_metronome(
            bpm=config['metronome']['bpm'],
            beats_per_measure=config['metronome']['beats_per_measure'],
            duration_seconds=total_duration,
            click_frequency=config['metronome']['click_frequency'],
            accent_frequency=config['metronome']['accent_frequency'],
            click_duration=config['metronome']['click_duration'],
            volume=config['metronome']['volume'],
            accent_first=True
        )
        print("  ✓ Metronome generated")
    else:
        base_audio = AudioSegment.silent(duration=total_duration * 1000)
        print("  ✓ Silent base track created (metronome disabled)")

    # 4. Calculate announcements
    print("\n[4/6] Calculating announcements...")
    announcements, all_texts = calculate_announcements(config)
    print(f"  ✓ {len(announcements)} announcements calculated")
    print(f"  ✓ {len(all_texts)} unique voice files needed")

    print(f"\n  First 10 announcements:")
    for ann in announcements[:10]:
        print(f"    {ann['time']:.1f}sec - {ann['text']}")

    # 5. Generate voice files
    print("\n[5/6] Generating voice files...")
    try:
        tts = get_tts_from_config(config)
        voice_dir = Path("output/voices")
        voice_dir.mkdir(parents=True, exist_ok=True)

        # Sort texts for consistent output
        def sort_key(text):
            import re
            nums = re.findall(r'\d+', text)
            if nums:
                return (0, int(nums[0]))
            return (1, text)

        sorted_texts = sorted(all_texts, key=sort_key)
        print(f"    Generating {len(sorted_texts)} voice files...")

        voice_files_map = tts.generate_multiple_speeches(
            texts=sorted_texts,
            output_dir=voice_dir,
            max_workers=10
        )
        print(f"  ✓ All voice files generated")

    except Exception as e:
        print(f"  ✗ Voice generation failed: {str(e)}")
        return

    # 6. Mix and export
    print("\n[6/6] Mixing and exporting...")
    final_audio = audio_gen.mix_audio_with_voice(
        base_audio=base_audio,
        voice_files_map=voice_files_map,
        announcements=announcements,
        voice_volume=config['voice']['volume']
    )

    output_path = Path("output") / config['output']['filename']
    audio_gen.export_audio(final_audio, output_path, format=config['output']['format'])

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Export successful!")
    print(f"    - File: {output_path}")
    print(f"    - Size: {file_size_mb:.2f} MB")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)
    print(f"\nUsage:")
    print(f"  1. Transfer '{output_path.name}' to your device/earbuds")
    print(f"  2. Press play, wait for countdown")
    print(f"  3. Start when you hear 'Go!'")
    print(f"  4. Listen for distance announcements to check your pace")
    print("=" * 60)


if __name__ == "__main__":
    main()
