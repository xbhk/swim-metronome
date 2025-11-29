#!/usr/bin/env python3
"""
Swim Metronome Generator
Generate metronome audio with voice announcements based on config
"""

import yaml
from pathlib import Path
from pydub import AudioSegment

from tts_service import get_tts_service
from audio_generator import AudioGenerator


def load_config(config_path="config.yaml"):
    """Load configuration file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_pace(pace_str):
    """
    Parse pace string, supports "1:45" format

    Args:
        pace_str: Pace string like "1:45" or "2:30"

    Returns:
        int: Seconds
    """
    if ':' in str(pace_str):
        parts = str(pace_str).split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes * 60 + seconds
    else:
        return int(pace_str)


def process_config(config):
    """
    Process config, calculate actual parameters

    - Parse pace format
    - Calculate duration from distance
    - Add warmup_time to total duration
    """
    # 1. Parse pace
    if 'pace' in config['target']:
        time_per_100m = parse_pace(config['target']['pace'])
        config['target']['time_per_100m'] = time_per_100m
    elif 'time_per_100m' not in config['target']:
        raise ValueError("Must set target.pace or target.time_per_100m")

    # 2. Calculate audio duration (without warmup)
    if 'distance' in config['target']:
        distance = config['target']['distance']
        time_per_100m = config['target']['time_per_100m']
        buffer_time = config['audio'].get('buffer_time', 60)

        swim_time = (distance / 100) * time_per_100m
        swim_duration = int(swim_time + buffer_time)

        config['audio']['swim_duration'] = swim_duration
    elif 'duration' not in config['audio']:
        raise ValueError("Must set target.distance or audio.duration")
    else:
        config['audio']['swim_duration'] = config['audio']['duration']

    # 3. Add warmup time to total duration
    warmup_time = config['audio'].get('warmup_time', 0)
    config['audio']['duration'] = config['audio']['swim_duration'] + warmup_time

    return config


def get_tts_from_config(config):
    """
    Create TTS service based on config

    Args:
        config: Configuration dict

    Returns:
        TTS service instance
    """
    voice_config = config['voice']
    provider = voice_config.get('tts_provider', 'edge')

    if provider == 'edge':
        edge_config = voice_config.get('edge', {})
        return get_tts_service(
            provider='edge',
            voice=edge_config.get('voice_en'),  # Will auto-detect language
            rate=edge_config.get('rate', '+0%')
        )
    elif provider == 'openai':
        openai_config = voice_config.get('openai', {})
        return get_tts_service(
            provider='openai',
            api_key=openai_config.get('api_key') or None,
            base_url=openai_config.get('base_url') or None,
            voice=openai_config.get('voice_model', 'nova'),
            model=openai_config.get('tts_model', 'tts-1')
        )
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def main():
    """Main program"""
    print("=" * 60)
    print("Swim Metronome Generator")
    print("=" * 60)

    # 1. Load config
    print("\n[1/7] Loading configuration...")
    config = load_config()
    config = process_config(config)

    time_per_100m = config['target']['time_per_100m']
    duration = config['audio']['duration']
    swim_duration = config['audio']['swim_duration']
    warmup_time = config['audio'].get('warmup_time', 0)

    print(f"  ✓ Configuration loaded")
    print(f"    - Pool length: {config['pool']['length']}m")
    print(f"    - Target pace: {time_per_100m}sec/100m "
          f"({time_per_100m//60}min {time_per_100m%60}sec)")

    if 'distance' in config['target']:
        distance = config['target']['distance']
        swim_time = (distance / 100) * time_per_100m
        print(f"    - Target distance: {distance}m")
        print(f"    - Estimated swim time: {int(swim_time//60)}min {int(swim_time%60)}sec")

    if warmup_time > 0:
        print(f"    - Warmup time: {warmup_time}sec")
        print(f"    - Swim audio duration: {swim_duration}sec ({swim_duration//60}min {swim_duration%60}sec)")
        print(f"    - Total duration: {duration}sec ({duration//60}min {duration%60}sec)")
    else:
        print(f"    - Total duration: {duration}sec ({duration//60}min {duration%60}sec)")

    # 2. Initialize audio generator
    print("\n[2/7] Initializing audio generator...")
    audio_gen = AudioGenerator(sample_rate=config['audio']['sample_rate'])
    print("  ✓ Audio generator initialized")

    # 3. Generate metronome (if enabled)
    base_audio = None
    if config['metronome']['enabled']:
        print("\n[3/7] Generating metronome...")
        print(f"    - BPM: {config['metronome']['bpm']}")
        print(f"    - Beats per measure: {config['metronome']['beats_per_measure']}")
        print(f"    - Volume: {config['metronome']['volume']}")

        # Generate warmup phase metronome
        print(f"    - Generating warmup phase ({warmup_time}sec)")
        warmup_metronome = audio_gen.generate_metronome(
            bpm=config['metronome']['bpm'],
            beats_per_measure=config['metronome']['beats_per_measure'],
            duration_seconds=warmup_time,
            click_frequency=config['metronome']['click_frequency'],
            accent_frequency=config['metronome']['accent_frequency'],
            click_duration=config['metronome']['click_duration'],
            volume=config['metronome']['volume'],
            accent_first=config['metronome']['accent_first']
        )

        # Generate swim phase metronome
        print(f"    - Generating swim phase ({swim_duration}sec)")
        swim_metronome = audio_gen.generate_metronome(
            bpm=config['metronome']['bpm'],
            beats_per_measure=config['metronome']['beats_per_measure'],
            duration_seconds=swim_duration,
            click_frequency=config['metronome']['click_frequency'],
            accent_frequency=config['metronome']['accent_frequency'],
            click_duration=config['metronome']['click_duration'],
            volume=config['metronome']['volume'],
            accent_first=config['metronome']['accent_first']
        )

        # Concatenate warmup and swim phase
        base_audio = warmup_metronome + swim_metronome
        print("  ✓ Metronome generated (warmup + swim)")
    else:
        print("\n[3/7] Metronome disabled, using silent track...")
        base_audio = AudioSegment.silent(duration=config['audio']['duration'] * 1000)
        print("  ✓ Silent track created")

    # 4. Calculate voice announcement times
    print("\n[4/7] Calculating voice announcement times...")
    announcements = []
    all_texts = set()

    # 4.1 Add warmup announcements
    if warmup_time > 0 and 'warmup_announcements' in config['audio']:
        print(f"  Warmup announcements:")
        for warmup_ann in config['audio']['warmup_announcements']:
            actual_time = warmup_time - warmup_ann['time']
            text = warmup_ann['text']
            all_texts.add(text)
            announcements.append({
                'time': actual_time,
                'text': text,
                'distance': 0
            })
            print(f"    {actual_time:.1f}sec - {text}")

    # 4.2 Calculate swim phase announcements
    print(f"\n  Swim announcements:")
    for ann_config in config['voice']['announcements']:
        interval = ann_config['interval']
        format_str = ann_config['format']

        ann_list = audio_gen.calculate_announcement_times(
            pool_length=config['pool']['length'],
            time_per_100m=config['target']['time_per_100m'],
            interval=interval,
            total_duration=swim_duration
        )

        for ann in ann_list:
            text = format_str.format(
                distance=ann['distance'],
                laps=int(ann['laps']),
                hundreds=ann['hundreds']
            )
            all_texts.add(text)
            ann['text'] = text
            ann['time'] += warmup_time
            announcements.append(ann)

    # Sort by time
    announcements.sort(key=lambda x: x['time'])

    print(f"\n  ✓ Calculated {len(announcements)} announcement times")
    print(f"  ✓ Need to generate {len(all_texts)} different voice files")
    print(f"\n  First 10 announcements:")
    for ann in announcements[:10]:
        print(f"    {ann['time']:.2f}sec - {ann['text']}")

    # 5. Generate voice files (if enabled)
    voice_files_map = {}
    if config['voice']['enabled']:
        print("\n[5/7] Generating voice files...")
        provider = config['voice'].get('tts_provider', 'edge')
        print(f"    - TTS Provider: {provider}")

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
                else:
                    return (1, text)

            all_texts_list = sorted(list(all_texts), key=sort_key)

            print(f"    Generating {len(all_texts_list)} voice files...")

            voice_files_map = tts.generate_multiple_speeches(
                texts=all_texts_list,
                output_dir=voice_dir,
                max_workers=10
            )

            print(f"  ✓ All voice files generated")

        except Exception as e:
            print(f"  ✗ Voice generation failed: {str(e)}")
            if provider == 'openai':
                print("  Tip: Check OPENAI_API_KEY or switch to 'edge' provider (free)")
            return

    else:
        print("\n[5/7] Voice announcements disabled")

    # 6. Mix audio
    print("\n[6/7] Mixing audio...")
    if config['voice']['enabled'] and voice_files_map:
        final_audio = audio_gen.mix_audio_with_voice(
            base_audio=base_audio,
            voice_files_map=voice_files_map,
            announcements=announcements,
            voice_volume=config['voice']['volume']
        )
    else:
        final_audio = base_audio

    print("  ✓ Audio mixing complete")

    # 7. Export final file
    output_path = Path("output") / config['audio']['output_filename']
    print(f"\n[7/7] Exporting audio to: {output_path}")
    audio_gen.export_audio(final_audio, output_path, format=config['audio']['format'])

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Export successful!")
    print(f"    - File size: {file_size_mb:.2f} MB")
    if warmup_time > 0:
        print(f"    - Total duration: {duration}sec ({duration//60}min {duration%60}sec)")
        print(f"      · Warmup: 0-{warmup_time}sec (countdown)")
        print(f"      · Swim: {warmup_time}-{duration}sec")
    else:
        print(f"    - Duration: {duration}sec ({duration//60}min {duration%60}sec)")

    print("\n" + "=" * 60)
    print("Generation complete!")
    print("=" * 60)
    if warmup_time > 0:
        print("Usage:")
        print(f"  1. Play audio, first {warmup_time}sec is warmup countdown")
        print(f"  2. Start swimming when you hear \"Go!\"")
        print(f"  3. Follow the metronome to maintain pace")
        print(f"  4. Listen for voice announcements for distance")
    print("\nTransfer the file to your waterproof earbuds.")
    print("=" * 60)


if __name__ == "__main__":
    main()
