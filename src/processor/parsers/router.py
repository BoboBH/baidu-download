"""
Unified processor routing system for multi-message type support.

This module implements a priority-based router that directs messages to appropriate processors
based on message type, with built-in error handling and workflow orchestration.
"""
from typing import Optional, List
from dataclasses import dataclass

from src.feishu.models import ParseResult
from src.utils.logger import get_logger


@dataclass
class RouterResult:
    """
    Unified result from router processing workflow.

    Attributes:
        message_type: Original message type
        success: Whether the entire workflow succeeded
        download_result: Result from download step
        process_result: Result from process step
        upload_files: List of files ready for upload
        error: Error message if any step failed
        processor_used: Which processor handled this message
    """
    message_type: str
    success: bool
    download_result: Optional[object] = None
    process_result: Optional[object] = None
    upload_files: List[dict] = None
    error: Optional[str] = None
    processor_used: Optional[str] = None

    def __post_init__(self):
        if self.upload_files is None:
            self.upload_files = []


class ProcessorRouter:
    """
    Unified processor routing system with priority-based message handling.

    Priority order:
    1. BaiduPanProcessor (highest) - handles 'baidupan' messages
    2. PdfLinkProcessor (medium) - handles 'pdf_link' messages
    3. DingTalkFileProcessor (lower) - handles 'dingtalk_pdf', 'dingtalk_zip' messages

    Features:
    - Priority-based processor registration
    - Automatic message type routing
    - Complete workflow orchestration (download → process → get_upload_files)
    - Comprehensive error handling and classification
    - Processor cleanup management
    """

    def __init__(self, settings):
        """
        Initialize processor router with settings.

        Args:
            settings: Application settings object
        """
        self.settings = settings
        self.processors = []  # Ordered list of processor objects (highest priority first)
        self._processors_with_priority = []  # Internal list of (priority, processor) tuples
        self.logger = get_logger(__name__)

        # Register processors with priority
        self._register_default_processors()

    def _register_default_processors(self):
        """Register default processors with priority ordering."""
        # Priority 1: BaiduPan (highest)
        try:
            from src.processor.parsers.baidupan_processor import BaiduPanProcessor
            baidupan_processor = BaiduPanProcessor(self.settings)
            self.register_processor(baidupan_processor, priority=1)
            self.logger.info("Registered BaiduPanProcessor with priority 1")
        except ImportError as e:
            self.logger.warning(f"Could not import BaiduPanProcessor: {e}")

        # Priority 2: PDF (medium)
        try:
            from src.processor.parsers.pdf_processor import PdfLinkProcessor
            pdf_processor = PdfLinkProcessor(self.settings)
            self.register_processor(pdf_processor, priority=2)
            self.logger.info("Registered PdfLinkProcessor with priority 2")
        except ImportError as e:
            self.logger.warning(f"Could not import PdfLinkProcessor: {e}")

        # Priority 3: DingTalk (lower)
        try:
            from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor
            dingtalk_processor = DingTalkFileProcessor(self.settings)
            self.register_processor(dingtalk_processor, priority=3)
            self.logger.info("Registered DingTalkFileProcessor with priority 3")
        except ImportError as e:
            self.logger.warning(f"Could not import DingTalkFileProcessor: {e}")

    def register_processor(self, processor, priority: int):
        """
        Register processor with priority.

        Args:
            processor: Processor instance
            priority: Priority level (lower number = higher priority)
        """
        # Store tuple of (priority, processor) for sorting
        self._processors_with_priority.append((priority, processor))
        # Sort by priority (lower number = higher priority)
        self._processors_with_priority.sort(key=lambda x: x[0])

        # Update the public processors list with sorted processor objects
        self.processors = [proc for _, proc in self._processors_with_priority]

    def can_process(self, message_type: str) -> bool:
        """
        Check if any processor can handle the given message type.

        Args:
            message_type: Type of message to check

        Returns:
            True if any processor can process the message type
        """
        for processor in self.processors:
            if processor.can_process(message_type):
                return True
        return False

    def get_processor(self, message_type: str):
        """
        Get processor for the given message type based on priority.

        Args:
            message_type: Type of message

        Returns:
            Processor instance or None if no processor can handle it
        """
        for processor in self.processors:
            if processor.can_process(message_type):
                return processor
        return None

    def process_message(self, parse_result: ParseResult) -> RouterResult:
        """
        Route message to appropriate processor and execute full workflow.

        Workflow:
        1. Route to appropriate processor based on message_type
        2. Execute: download → process → get_upload_files
        3. Return unified result with all information
        4. Handle errors with proper classification

        Args:
            parse_result: ParseResult containing message information

        Returns:
            RouterResult with complete workflow execution results
        """
        message_type = parse_result.message_type
        self.logger.info(f"Processing message type: {message_type}")

        # Step 1: Get appropriate processor
        processor = self.get_processor(message_type)
        if not processor:
            error_msg = f"No processor available for message type: {message_type}"
            self.logger.error(error_msg)
            return RouterResult(
                message_type=message_type,
                success=False,
                error=error_msg
            )

        processor_name = processor.__class__.__name__
        self.logger.info(f"Using processor: {processor_name}")

        try:
            # Step 2: Download files
            self.logger.info(f"Step 1: Download files for {message_type}")
            download_result = processor.download(parse_result)

            if not download_result.success:
                error_msg = f"Download failed: {download_result.error}"
                self.logger.error(error_msg)
                return RouterResult(
                    message_type=message_type,
                    success=False,
                    download_result=download_result,
                    error=error_msg,
                    processor_used=processor_name
                )

            self.logger.info("Download completed successfully")

            # Step 3: Process files
            self.logger.info(f"Step 2: Process files for {message_type}")
            process_result = processor.process(download_result, parse_result)

            if not process_result.success:
                error_msg = f"Process failed: {process_result.error}"
                self.logger.error(error_msg)
                return RouterResult(
                    message_type=message_type,
                    success=False,
                    download_result=download_result,
                    process_result=process_result,
                    error=error_msg,
                    processor_used=processor_name
                )

            self.logger.info("Process completed successfully")

            # Step 4: Get upload files
            self.logger.info(f"Step 3: Get upload files for {message_type}")
            upload_files = processor.get_upload_files(process_result, parse_result)

            self.logger.info(f"Generated {len(upload_files)} upload file entries")

            # Step 5: Return success result
            return RouterResult(
                message_type=message_type,
                success=True,
                download_result=download_result,
                process_result=process_result,
                upload_files=upload_files,
                processor_used=processor_name
            )

        except Exception as e:
            error_msg = f"Unexpected error during processing: {str(e)}"
            self.logger.error(error_msg)
            return RouterResult(
                message_type=message_type,
                success=False,
                error=error_msg,
                processor_used=processor_name
            )

    def cleanup(self):
        """
        Clean up all processors.

        Calls cleanup method on each registered processor.
        """
        for processor in self.processors:
            try:
                if hasattr(processor, 'cleanup'):
                    processor.cleanup()
                    self.logger.debug(f"Cleaned up {processor.__class__.__name__}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {processor.__class__.__name__}: {e}")

        self.logger.info("All processors cleaned up")
