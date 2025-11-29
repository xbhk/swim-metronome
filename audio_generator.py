"""
Audio Generator Module
处理音频生成、节拍器创建和音频混合
"""

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine
from pathlib import Path


class AudioGenerator:
    """音频生成器"""

    def __init__(self, sample_rate=44100):
        """
        初始化音频生成器

        Args:
            sample_rate: 采样率，默认 44100 Hz
        """
        self.sample_rate = sample_rate

    def generate_click(self, frequency=800, duration=0.05, volume=0.5):
        """
        生成单个节拍声音（click）

        Args:
            frequency: 频率（Hz）
            duration: 持续时间（秒）
            volume: 音量（0-1）

        Returns:
            AudioSegment: 节拍声音
        """
        # 使用正弦波生成器
        click = Sine(frequency).to_audio_segment(duration=int(duration * 1000))

        # 添加淡入淡出效果，使声音更平滑
        click = click.fade_in(5).fade_out(5)

        # 调整音量
        click = click - (100 * (1 - volume))

        return click

    def generate_metronome(self, bpm, beats_per_measure, duration_seconds,
                          click_frequency=800, accent_frequency=1200,
                          click_duration=0.05, volume=0.5, accent_first=True):
        """
        生成节拍器音频

        Args:
            bpm: 每分钟节拍数
            beats_per_measure: 每小节拍数
            duration_seconds: 总持续时间（秒）
            click_frequency: 普通拍频率（Hz）
            accent_frequency: 重音拍频率（Hz）
            click_duration: 每次点击持续时间（秒）
            volume: 音量（0-1）
            accent_first: 第一拍是否为重音

        Returns:
            AudioSegment: 节拍器音频
        """
        # 计算每拍的时间间隔（毫秒）
        beat_interval_ms = (60 / bpm) * 1000

        # 生成普通拍和重音拍（普通拍和重音拍音量相同，只是频率不同）
        normal_click = self.generate_click(click_frequency, click_duration, volume)
        accent_click = self.generate_click(accent_frequency, click_duration, volume)

        # 创建静音基础轨道
        metronome = AudioSegment.silent(duration=duration_seconds * 1000)

        # 添加节拍
        current_time_ms = 0
        beat_count = 0
        total_beats = int(duration_seconds * 1000 / beat_interval_ms)
        print(f"  生成 {total_beats} 个节拍...")

        while current_time_ms < duration_seconds * 1000:
            # 每100个节拍显示一次进度
            if beat_count > 0 and beat_count % 100 == 0:
                progress = (beat_count / total_beats) * 100
                print(f"    进度: {beat_count}/{total_beats} ({progress:.1f}%)")
            # 判断是否为重音拍
            is_accent = (beat_count % beats_per_measure == 0) if accent_first else False

            # 选择合适的 click
            click = accent_click if is_accent else normal_click

            # 叠加到轨道上
            metronome = metronome.overlay(click, position=int(current_time_ms))

            # 移动到下一拍
            current_time_ms += beat_interval_ms
            beat_count += 1

        return metronome

    def calculate_announcement_times(self, pool_length, time_per_100m,
                                    interval, total_duration):
        """
        计算语音提示的时间点和内容

        Args:
            pool_length: 泳道长度（米）
            time_per_100m: 每100米的时间（秒）
            interval: 提示间隔距离（米）
            total_duration: 总持续时间（秒）

        Returns:
            list: [(时间(秒), 距离(米)), ...] 的列表
        """
        time_per_meter = time_per_100m / 100  # 每米的时间
        announcements = []

        distance = interval  # 从第一个间隔开始
        while True:
            time = distance * time_per_meter
            if time >= total_duration:
                break

            announcements.append({
                'time': time,
                'distance': distance,
                'laps': distance / pool_length,
                'hundreds': distance / 100
            })

            distance += interval

        return announcements

    def mix_audio_with_voice(self, base_audio, voice_files_map,
                           announcements, voice_volume=0.8):
        """
        将语音提示混合到基础音频中

        Args:
            base_audio: 基础音频（AudioSegment），可以是节拍器或静音
            voice_files_map: {文本: 文件路径} 的字典
            announcements: 提示信息列表，每项包含 time 和 distance
            voice_volume: 语音音量（0-1）

        Returns:
            AudioSegment: 混合后的音频
        """
        result = base_audio
        total = len(announcements)
        print(f"  混合 {total} 个语音提示...")

        for idx, announcement in enumerate(announcements, 1):
            if idx % 10 == 0:
                print(f"    混合进度: {idx}/{total} ({idx/total*100:.1f}%)")
            time_ms = int(announcement['time'] * 1000)

            # 使用 announcement 中的 text 字段（支持准备阶段和游泳阶段）
            text = announcement.get('text')
            if not text:
                # 如果没有 text 字段，使用 distance 生成
                distance = announcement['distance']
                text = f"{distance}米"

            # 获取对应的语音文件
            if text in voice_files_map:
                voice_file = voice_files_map[text]
                voice_audio = AudioSegment.from_mp3(voice_file)

                # 调整音量
                voice_audio = voice_audio - (100 * (1 - voice_volume))

                # 混合到结果中
                result = result.overlay(voice_audio, position=time_ms)
                print(f"  + 添加语音: {text} @ {announcement['time']:.2f}秒")

        return result

    def export_audio(self, audio, output_path, format="mp3"):
        """
        导出音频文件

        Args:
            audio: AudioSegment 对象
            output_path: 输出文件路径
            format: 输出格式（mp3 或 wav）

        Returns:
            Path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        audio.export(output_path, format=format)
        return output_path


def test_audio_generator():
    """测试音频生成器"""
    print("测试音频生成器...")

    generator = AudioGenerator()

    # 测试生成10秒的节拍器
    print("生成测试节拍器（10秒，BPM 41，每6拍1重音）...")
    metronome = generator.generate_metronome(
        bpm=41,
        beats_per_measure=6,
        duration_seconds=10,
        volume=0.3
    )

    # 导出测试文件
    output_path = Path("output/test_metronome.mp3")
    generator.export_audio(metronome, output_path)

    print(f"✓ 测试成功！文件已保存到: {output_path}")
    print(f"  文件大小: {output_path.stat().st_size} bytes")

    # 测试计算提示时间
    print("\n测试计算提示时间...")
    announcements = generator.calculate_announcement_times(
        pool_length=25,
        time_per_100m=105,
        interval=25,
        total_duration=300  # 5分钟
    )

    print(f"  前5个提示时间点:")
    for ann in announcements[:5]:
        print(f"    {ann['time']:.2f}秒 - {ann['distance']}米")


if __name__ == "__main__":
    test_audio_generator()
