"""
DingTalk file parser for DingTalk file messages.
"""
from typing import Optional, Dict, Any
from src.feishu.models import ParseResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DingTalkFileParser:
    """
    Parser for DingTalk file messages.

    Handles messages containing file attachments from DingTalk,
    supporting PDF and ZIP file types.
    """

    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['.pdf', '.zip']

    def parse(self, message_data: Dict[str, Any], source: str = 'dingtalk') -> Optional[ParseResult]:
        """
        Parse DingTalk file message.

        Args:
            message_data: DingTalk message data as dictionary
            source: Message source (default: dingtalk)

        Returns:
            ParseResult with message_type='dingtalk_pdf' or 'dingtalk_zip'
            None if file type is not supported or required fields are missing
        """
        if not message_data or not isinstance(message_data, dict):
            logger.warning("Invalid message data for DingTalk file parsing")
            return None

        # Extract file information
        file_name = self._extract_file_name(message_data)
        if not file_name:
            logger.warning("No file name found in DingTalk message")
            return None

        # Check if file extension is supported
        file_extension = self._get_file_extension(file_name)
        if not self._is_supported_extension(file_extension):
            logger.debug(f"Unsupported file type: {file_extension} in {file_name}")
            return None

        # Extract required fields
        file_id = message_data.get('fileId') or message_data.get('file_id')
        space_id = message_data.get('spaceId') or message_data.get('space_id')
        download_code = message_data.get('downloadCode') or message_data.get('download_code')

        if not file_id:
            logger.warning(f"Missing file_id in DingTalk message: {file_name}")
            return None

        if not space_id:
            logger.warning(f"Missing space_id in DingTalk message: {file_name}")
            return None

        # Determine message type based on file extension
        if file_extension == '.pdf':
            message_type = 'dingtalk_pdf'
        elif file_extension == '.zip':
            message_type = 'dingtalk_zip'
        else:
            logger.warning(f"Unsupported file type: {file_extension}")
            return None

        # Use file_id:space_id as unique identifier (stable, not download_code)
        unique_identifier = f"{file_id}:{space_id}"

        logger.info(f"DingTalk file parsed: type={message_type}, file={file_name}, id={unique_identifier}")

        return ParseResult(
            message_type=message_type,
            unique_identifier=unique_identifier,
            source=source,
            file_id=file_id,
            space_id=space_id,
            download_code=download_code,
            file_name=file_name
        )

    def _extract_file_name(self, message_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract file name from message data.

        Args:
            message_data: Message data dictionary

        Returns:
            File name or None if not found
        """
        # Try different possible keys
        file_name = (message_data.get('fileName') or
                     message_data.get('file_name') or
                     message_data.get('name'))

        if file_name and isinstance(file_name, str):
            return file_name.strip()

        return None

    def _get_file_extension(self, file_name: str) -> str:
        """
        Get file extension from file name.

        Args:
            file_name: File name

        Returns:
            File extension including dot (e.g., '.pdf')
        """
        if not file_name:
            return ''

        # Extract extension
        if '.' in file_name:
            extension = file_name.rsplit('.', 1)[-1].lower()
            # Add dot if not present
            return f'.{extension}'

        return ''

    def _is_supported_extension(self, extension: str) -> bool:
        """
        Check if file extension is supported.

        Args:
            extension: File extension (e.g., '.pdf')

        Returns:
            True if extension is supported
        """
        if not extension:
            return False

        # Normalize extension (ensure it starts with dot)
        if not extension.startswith('.'):
            extension = f'.{extension}'

        return extension.lower() in self.SUPPORTED_EXTENSIONS

    def can_process(self, message_type: str) -> bool:
        """
        Check if this parser can process the given message type.

        Args:
            message_type: Type of message to check

        Returns:
            True if this parser can process the message type
        """
        return message_type in ('dingtalk_pdf', 'dingtalk_zip')
