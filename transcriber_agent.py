"""
Transcriber Agent that converts audio to text and identifies speakers.
"""

import os
import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple
import tempfile

import speech_recognition as sr
from pydub import AudioSegment
import librosa
import numpy as np
from openai import OpenAI

from .base_agent import BaseAgent
from ..core.message import Message, MessageType
from ..utils.audio_processing import AudioProcessor
from ..models.meeting import MeetingTranscript, TranscriptSegment

class TranscriberAgent(BaseAgent):
    """
    Agent responsible for transcribing audio into text with speaker identification.
    Supports both live audio input and pre-recorded audio files.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Transcriber Agent.
        
        Args:
            config_path (Optional[str]): Path to custom config file
        """
        super().__init__("transcriber", config_path)
        
        # Initialize OpenAI client for transcription if configured to use it
        self.openai_client = None
        if self.config["llm"]["provider"] == "openai":
            self.openai_client = OpenAI(
                api_key=self.config["llm"]["api_key"]
            )
        
        # Audio configuration
        self.sample_rate = self.agent_config.get("sample_rate", 16000)
        self.channels = self.agent_config.get("channels", 1)
        self.chunk_size = self.agent_config.get("chunk_size", 1024)
        self.silence_threshold = self.agent_config.get("silence_threshold", 500)
        self.silence_duration = self.agent_config.get("silence_duration", 1.0)
        
        # Speaker diarization settings
        self.speaker_diarization = self.agent_config.get("speaker_diarization", True)
        self.min_speaker_segments = self.agent_config.get("min_speaker_segments", 3)
        
        # Confidence threshold for accepting transcriptions
        self.confidence_threshold = self.agent_config.get("confidence_threshold", 0.85)
        
        # Audio processing utilities
        self.audio_processor = AudioProcessor(
            sample_rate=self.sample_rate,
            channels=self.channels,
            chunk_size=self.chunk_size,
            silence_threshold=self.silence_threshold,
            silence_duration=self.silence_duration
        )
        
        # For live audio recording
        self.recognizer = sr.Recognizer()
        self.is_recording = False
        self.current_recording = None
        
        self.logger.info("Transcriber Agent initialized")
    
    def get_subscribed_events(self) -> List[str]:
        """
        Get the events this agent subscribes to.
        
        Returns:
            List[str]: List of event types
        """
        return [
            MessageType.AUDIO_CAPTURED.name,
            MessageType.SYSTEM_COMMAND.name
        ]
    
    def handle_message(self, message: Message):
        """
        Handle incoming messages.
        
        Args:
            message (Message): The message to handle
        """
        if message.type == MessageType.AUDIO_CAPTURED:
            self.process_audio(message)
        elif message.type == MessageType.SYSTEM_COMMAND:
            command = message.content.get("command")
            if command == "start_recording":
                self.start_recording(message)
            elif command == "stop_recording":
                self.stop_recording(message)
    
    def start_recording(self, message: Message):
        """
        Start recording live audio.
        
        Args:
            message (Message): The command message
        """
        if self.is_recording:
            self.logger.warning("Already recording")
            return
        
        meeting_id = message.content.get("meeting_id")
        if not meeting_id:
            meeting_id = f"meeting_{int(time.time())}"
        
        # Initialize recording state
        self.is_recording = True
        self.current_recording = {
            "meeting_id": meeting_id,
            "start_time": time.time(),
            "audio_chunks": [],
            "audio_file": None
        }
        
        self.logger.info(f"Started recording for meeting {meeting_id}")
        
        # Start recording in a separate thread
        self._record_audio()
    
    def _record_audio(self):
        """Record audio in chunks and process for silence detection."""
        try:
            with sr.Microphone(sample_rate=self.sample_rate) as source:
                self.recognizer.adjust_for_ambient_noise(source)
                
                while self.is_recording:
                    try:
                        # Record a chunk of audio
                        audio_data = self.recognizer.listen(
                            source, 
                            timeout=5, 
                            phrase_time_limit=10
                        )
                        
                        # Store the audio chunk
                        self.current_recording["audio_chunks"].append(audio_data)
                        
                        # Process this chunk if we have enough data
                        if len(self.current_recording["audio_chunks"]) >= 3:
                            self._process_recording_chunk()
                            
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        self.logger.error(f"Error during audio recording: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error setting up audio recording: {e}")
            self.is_recording = False
    
    def _process_recording_chunk(self):
        """Process a chunk of the current recording."""
        # Combine audio chunks into a single audio segment
        # This is a simplified implementation and would need proper buffering in production
        
        # For this demo, we'll just send a notification that audio chunks are available
        message = Message(
            type=MessageType.AUDIO_CAPTURED,
            content={
                "meeting_id": self.current_recording["meeting_id"],
                "audio_chunks": len(self.current_recording["audio_chunks"]),
                "recording_duration": time.time() - self.current_recording["start_time"],
                "live_recording": True
            }
        )
        self.send_message(message)
    
    def stop_recording(self, message: Message):
        """
        Stop recording live audio and process the final recording.
        
        Args:
            message (Message): The command message
        """
        if not self.is_recording:
            self.logger.warning("Not currently recording")
            return
        
        # Stop the recording
        self.is_recording = False
        
        # Combine all audio chunks and save to a file
        if self.current_recording and self.current_recording["audio_chunks"]:
            try:
                # Create a temporary file to save the combined audio
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                )
                self.current_recording["audio_file"] = temp_file.name
                
                # Get raw audio data from all chunks
                combined_audio = AudioSegment.empty()
                for chunk in self.current_recording["audio_chunks"]:
                    chunk_audio = AudioSegment(
                        data=chunk.get_raw_data(),
                        sample_width=chunk.sample_width,
                        frame_rate=chunk.sample_rate,
                        channels=1
                    )
                    combined_audio += chunk_audio
                
                # Export to WAV file
                combined_audio.export(temp_file.name, format="wav")
                
                # Process the complete recording
                self.process_audio_file(temp_file.name, self.current_recording["meeting_id"])
                
                self.logger.info(f"Recording saved to {temp_file.name}")
                
            except Exception as e:
                self.logger.error(f"Error saving recording: {e}")
        
        # Reset recording state
        self.current_recording = None
    
    def process_audio(self, message: Message):
        """
        Process an audio message, which could be a file path or raw audio data.
        
        Args:
            message (Message): The audio message to process
        """
        # Check if the message contains a file path
        audio_path = message.content.get("audio_path")
        meeting_id = message.content.get("meeting_id")
        
        if audio_path and os.path.exists(audio_path):
            self.process_audio_file(audio_path, meeting_id)
        else:
            self.logger.error("Audio message does not contain a valid audio path")
    
    def process_audio_file(self, audio_path: str, meeting_id: Optional[str] = None):
        """
        Process an audio file and generate a transcript.
        
        Args:
            audio_path (str): Path to the audio file
            meeting_id (Optional[str]): ID of the meeting
        """
        if not meeting_id:
            meeting_id = f"meeting_{int(time.time())}"
        
        self.logger.info(f"Processing audio file for meeting {meeting_id}")
        
        try:
            # Pre-process the audio file
            processed_audio = self.audio_processor.preprocess_audio(audio_path)
            
            # Perform speaker diarization if enabled
            speaker_segments = []
            if self.speaker_diarization:
                speaker_segments = self._perform_speaker_diarization(processed_audio)
            
            # Transcribe the audio
            transcript = self._transcribe_audio(processed_audio, speaker_segments)
            
            # Create a meeting transcript object
            meeting_transcript = MeetingTranscript(
                meeting_id=meeting_id,
                transcript_segments=transcript,
                start_time=time.time(),
                end_time=time.time(),
                audio_path=audio_path
            )
            
            # Send the transcript to other agents
            self._send_transcription_message(meeting_transcript)
            
            self.logger.info(f"Transcription completed for meeting {meeting_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing audio file: {e}")
            
            # Send error message
            error_message = Message(
                type=MessageType.ERROR,
                content={
                    "error": f"Transcription failed: {str(e)}",
                    "meeting_id": meeting_id,
                    "audio_path": audio_path
                }
            )
            self.send_message(error_message)
    
    def _perform_speaker_diarization(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Perform speaker diarization on an audio file.
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            List[Dict[str, Any]]: List of speaker segments with timestamps
        """
        self.logger.info("Performing speaker diarization")
        
        # For a more advanced implementation, you would use a specialized
        # speaker diarization library or service like pyannote.audio
        
        # For this simplified implementation, we'll use OpenAI's Whisper model
        # which can sometimes identify speakers in its transcription
        
        try:
            # Load audio using librosa
            audio, _ = librosa.load(audio_path, sr=self.sample_rate, mono=True)
            
            # Detect non-silent segments
            non_silent_segments = librosa.effects.split(
                audio, 
                top_db=20,
                frame_length=self.chunk_size,
                hop_length=self.chunk_size // 4
            )
            
            # Convert to seconds
            segments = []
            for i, (start, end) in enumerate(non_silent_segments):
                # Assign speakers in a round-robin fashion for demo purposes
                # In a real implementation, use a proper speaker diarization algorithm
                speaker = f"Speaker {(i % 4) + 1}"
                
                segments.append({
                    "start": float(start) / self.sample_rate,
                    "end": float(end) / self.sample_rate,
                    "speaker": speaker
                })
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Error in speaker diarization: {e}")
            return []
    
    def _transcribe_audio(
        self, 
        audio_path: str, 
        speaker_segments: List[Dict[str, Any]]
    ) -> List[TranscriptSegment]:
        """
        Transcribe audio file with speaker identification.
        
        Args:
            audio_path (str): Path to the audio file
            speaker_segments (List[Dict[str, Any]]): Speaker segments from diarization
            
        Returns:
            List[TranscriptSegment]: List of transcript segments with speakers
        """
        self.logger.info("Transcribing audio")
        
        transcript_segments = []
        
        try:
            # Use OpenAI's Whisper model for transcription
            with open(audio_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Process the response
            if hasattr(response, 'segments'):
                segments = response.segments
            else:
                # Fallback for older API versions or different response formats
                segments = json.loads(response).get('segments', [])
            
            # Match transcription segments with speaker segments
            for i, segment in enumerate(segments):
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)
                text = segment.get('text', '')
                
                # Find the speaker for this segment
                speaker = "Unknown Speaker"
                for speaker_segment in speaker_segments:
                    if (start_time >= speaker_segment["start"] and 
                        end_time <= speaker_segment["end"]):
                        speaker = speaker_segment["speaker"]
                        break
                
                # Create transcript segment
                transcript_segment = TranscriptSegment(
                    start_time=start_time,
                    end_time=end_time,
                    speaker=speaker,
                    text=text,
                    confidence=segment.get('confidence', 0.0)
                )
                
                transcript_segments.append(transcript_segment)
        
        except Exception as e:
            self.logger.error(f"Error in transcription: {e}")
        
        return transcript_segments
    
    def _send_transcription_message(self, transcript: MeetingTranscript):
        """
        Send the transcription to other agents.
        
        Args:
            transcript (MeetingTranscript): The meeting transcript
        """
        # Convert transcript to serializable format
        serializable_transcript = {
            "meeting_id": transcript.meeting_id,
            "start_time": transcript.start_time,
            "end_time": transcript.end_time,
            "audio_path": transcript.audio_path,
            "segments": [
                {
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "speaker": segment.speaker,
                    "text": segment.text,
                    "confidence": segment.confidence
                }
                for segment in transcript.transcript_segments
            ]
        }
        
        # Create and send message
        message = Message(
            type=MessageType.TRANSCRIPTION_COMPLETE,
            content={
                "transcript": serializable_transcript,
                "meeting_id": transcript.meeting_id
            },
            context_id=transcript.meeting_id
        )
        
        self.send_message(message)
