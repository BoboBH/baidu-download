# Quant Format Message Parsing Design

**Date:** 2026-08-17  
**Author:** Claude  
**Status:** Design Approved - Pending Implementation  
**Related Issue:** Support for quant-style Baidu Pan message format

## Overview

This design adds support for a new Baidu Pan share link message format while maintaining full backward compatibility with existing message parsing formats.

## New Format Requirements

**Target format:**
```
quant-2026-3: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4
```

**Format specification:**
- **Folder name**: `quant-{yyyy}-{m}` where:
  - `quant` is a fixed prefix (case-sensitive)
  - `{yyyy}` is a 4-digit year (2024, 2025, 2026, etc.)
  - `{m}` is a 1-2 digit month (1-12)
- **Separator**: Colon (`:`) with optional whitespace
- **URL**: Standard Baidu Pan share link
- **Extraction code**: Embedded in URL as `?pwd=xxx` parameter

**Examples:**
- `quant-2026-3: https://pan.baidu.com/s/xxx?pwd=gqi4` ✅
- `quant-2026-10: https://pan.baidu.com/s/xxx?pwd=abcd` ✅
- `quant-2026-11: https://pan.baidu.com/s/xxx?pwd=xyz1` ✅
- `quant-2026-12: https://pan.baidu.com/s/xxx` ✅ (pwd optional)
- `research-2026-3: https://...` ❌ (wrong prefix)
- `report-2026-11: https://...` ❌ (wrong prefix)

## Architecture

### Current Architecture
```
Message content → Combined pattern (6-digit + link) → Link-only pattern → Return result
```

### New Architecture
```
Message content → Quant pattern (quant-yyyy-m: link?pwd=xxx) → Combined pattern (6-digit + link) → Link-only pattern → Return result
```

**Key Design Principles:**
1. **Priority-based pattern matching**: Quant format checked first
2. **Backward compatibility**: All existing formats continue to work
3. **Single responsibility**: Each format has dedicated pattern and logic
4. **Clear separation**: New code isolated from existing logic

## Implementation Details

### 1. Pattern Matching

**New regex pattern:**
```python
QUANT_PATTERN = re.compile(
    r'(quant-\d{4}-\d{1,2})\s*:\s*(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?)'
)
```

**Pattern breakdown:**
- `(quant-\d{4}-\d{1,2})` - Captures folder name with quant prefix, 4-digit year, 1-2 digit month
- `\s*:\s*` - Colon separator with optional whitespace
- `(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?)` - Captures URL with optional pwd parameter

### 2. URL Extraction Code Parsing

**New helper method:**
```python
def extract_pwd_from_url(self, url: str) -> Optional[str]:
    """
    从百度网盘URL中提取pwd参数作为提取码
    
    Args:
        url: 百度网盘分享链接
        
    Returns:
        提取码，如果URL中没有pwd参数则返回None
    """
    pwd_pattern = re.compile(r'[?&]pwd=([a-zA-Z0-9]+)')
    match = pwd_pattern.search(url)
    if match:
        return match.group(1)
    return None
```

**Logic:**
- Extracts `pwd` parameter from URL (supports both `?pwd=` and `&pwd=` formats)
- Returns extraction code, or `None` if not present
- Used immediately after matching quant pattern
- Falls back to config extraction code if URL lacks `pwd` parameter

### 3. Updated Parsing Flow

**Modified `parse_message()` method:**
```python
def parse_message(self, content: str, source: str = 'feishu') -> Optional[ParseResult]:
    # ... (existing JSON parsing and content cleanup)
    
    # 1. NEW: Try quant format first (highest priority)
    quant_match = self.QUANT_PATTERN.search(content)
    if quant_match:
        folder_name = quant_match.group(1)  # quant-2026-3
        share_link = quant_match.group(2).strip()
        
        # Validate URL was captured
        if not share_link:
            logger.warning(f"Quant format matched but no URL found: {content[:50]}...")
            return None
            
        # Optional: Validate month range (1-12)
        month_part = folder_name.split('-')[-1]
        try:
            month = int(month_part)
            if month < 1 or month > 12:
                logger.warning(f"Invalid month in folder name: {folder_name}")
                return None
        except ValueError:
            logger.warning(f"Invalid month format in folder name: {folder_name}")
            return None
        
        # Extract pwd from URL or use config default
        extraction_code = self.extract_pwd_from_url(share_link) or self.settings.message_default_extraction_code
        
        logger.info(f"Quant format parsed: {folder_name}")
        logger.debug(f"Extraction code: {extraction_code}, Share link: {share_link}")
        
        return ParseResult(
            source=source,
            share_link=share_link, 
            folder_name=folder_name, 
            extraction_code=extraction_code, 
            raw_content=content
        )
    
    # 2. Existing: Combined format (6-digit + link)
    # ... (existing combined format logic - unchanged)
    
    # 3. Existing: Link-only format  
    # ... (existing link-only logic - unchanged)
```

### 4. Error Handling

**Validation rules:**
- **Invalid month validation**: Reject months < 1 or > 12
- **Missing URL**: If quant pattern matches folder name but no URL, return None
- **Malformed URL**: If URL doesn't contain valid Baidu Pan domain, existing pattern handles this
- **Missing pwd parameter**: Not an error - use config extraction code
- **Invalid month format**: Reject non-numeric month values

**Error handling approach:**
- Log warnings with context for debugging
- Return None for invalid formats (consistent with existing behavior)
- Maintain existing error handling patterns

### 5. Logging and Debugging

**Enhanced logging for quant format:**
```python
logger.info(f"Quant format parsed: {folder_name}")
logger.debug(f"Extraction code from URL: {extraction_code}")
logger.debug(f"Share link: {share_link}")
logger.debug(f"Raw content: {content[:100]}...")
```

**Debug benefits:**
- Clear identification of quant format parsing
- Visibility into extraction code source (URL vs config)
- Easy troubleshooting of pattern matching issues

## Backward Compatibility

**Guaranteed compatibility:**
- All existing message formats work exactly as before
- 6-digit folder name format: `260723：https://...`
- Link-only format: `https://...`
- Priority system ensures quant format doesn't interfere with existing patterns
- No changes to existing ParseResult data structure
- No changes to database schema, downloader, uploader, or other components

**Compatibility testing:**
- Existing unit tests continue to pass
- New tests don't modify existing test behavior
- Manual testing with real messages confirms compatibility

## Testing Strategy

### Unit Test Coverage

```python
# Test quant format with pwd parameter
def test_parse_quant_format_with_pwd():
    parser = MessageParser()
    content = "quant-2026-3: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"
    result = parser.parse_message(content)
    assert result is not None
    assert result.folder_name == "quant-2026-3"
    assert result.extraction_code == "gqi4"
    assert result.share_link == "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"

# Test quant format without pwd parameter (fallback to config)
def test_parse_quant_format_without_pwd():
    content = "quant-2026-10: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA"
    result = parser.parse_message(content)
    assert result is not None
    assert result.folder_name == "quant-2026-10"  
    assert result.extraction_code == "0409"  # config default

# Test various month formats
def test_parse_quant_format_different_months():
    parser = MessageParser()
    
    # Single digit month
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result.folder_name == "quant-2026-3"
    
    # Double digit months
    result = parser.parse_message("quant-2026-10: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result.folder_name == "quant-2026-10"
    
    result = parser.parse_message("quant-2026-11: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result.folder_name == "quant-2026-11"
    
    result = parser.parse_message("quant-2026-12: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result.folder_name == "quant-2026-12"

# Test rejection of other prefixes
def test_reject_other_prefixes():
    parser = MessageParser()
    assert parser.parse_message("research-2026-3: https://pan.baidu.com/s/xxx?pwd=abc") is None
    assert parser.parse_message("report-2026-11: https://pan.baidu.com/s/xxx?pwd=abc") is None
    assert parser.parse_message("data-2026-5: https://pan.baidu.com/s/xxx?pwd=abc") is None

# Test rejection of invalid months
def test_reject_invalid_months():
    parser = MessageParser()
    assert parser.parse_message("quant-2026-0: https://pan.baidu.com/s/xxx?pwd=abc") is None
    assert parser.parse_message("quant-2026-13: https://pan.baidu.com/s/xxx?pwd=abc") is None
    assert parser.parse_message("quant-2026-99: https://pan.baidu.com/s/xxx?pwd=abc") is None

# Test different spacing variations
def test_quant_format_spacing_variations():
    parser = MessageParser()
    
    # No spaces
    result = parser.parse_message("quant-2026-3:https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    
    # Spaces around colon
    result = parser.parse_message("quant-2026-3 : https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    
    # Multiple spaces
    result = parser.parse_message("quant-2026-3   :   https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None

# Test backward compatibility
def test_existing_formats_still_work():
    parser = MessageParser()
    
    # Combined format (6-digit + link)
    result = parser.parse_message("260723：https://pan.baidu.com/s/1abc123def456")
    assert result is not None
    assert result.folder_name == "260723"
    
    # Link-only format
    result = parser.parse_message("https://pan.baidu.com/s/1abc123def456")
    assert result is not None

# Test message source preservation
def test_quant_format_source_preservation():
    parser = MessageParser()
    
    # Feishu source (default)
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result.source == "feishu"
    
    # DingTalk source
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc", source="dingtalk")
    assert result.source == "dingtalk"

# Test URL extraction code parsing
def test_extract_pwd_from_url():
    parser = MessageParser()
    
    # With ?pwd= parameter
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx?pwd=gqi4") == "gqi4"
    
    # With &pwd= parameter  
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx?foo=bar&pwd=abcd") == "abcd"
    
    # Without pwd parameter
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx") is None
```

### Manual Testing

**Test scenarios:**
1. Send actual quant-format messages from Feishu
2. Send actual quant-format messages from DingTalk
3. Verify folder creation with quant-style names
4. Confirm extraction code works for downloads
5. Test database logging with new format
6. Verify existing message types still work

## Implementation Scope

### Files to Modify

**Primary changes:**
- `src/feishu/message_parser.py` - Add quant pattern, helper method, and updated parsing logic
- `test/unit/test_message_parser.py` - Add comprehensive unit tests

### No Changes Needed

- Database schema (ParseResult unchanged)
- Downloader components (extraction code handling unchanged)
- Uploader components (folder name handling unchanged)
- Configuration files
- Other components in the processing pipeline

### Estimated Complexity

**Low complexity** - Focused changes in single file with clear scope, minimal risk to existing functionality.

## Success Criteria

**Implementation successful when:**
1. Quant format messages are correctly parsed and processed
2. Extraction codes from URLs are properly used for downloads
3. Folder names with quant-style names are created correctly
4. All existing message formats continue to work unchanged
5. All unit tests pass (new and existing)
6. Manual testing confirms end-to-end functionality
7. No regression in existing functionality

## Implementation Plan

Next steps after design approval:
1. Create detailed implementation plan using writing-plans skill
2. Implement core parsing changes in message_parser.py
3. Add comprehensive unit tests
4. Manual testing with real messages
5. Integration testing
6. Documentation updates if needed

## Appendix

### Examples of Supported Formats

**New quant format:**
```
quant-2026-3: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4
```

**Existing formats (unchanged):**
```
260723：https://pan.baidu.com/s/1abc123def456
这是今天的研报260807 https://pan.baidu.com/s/xxx
链接 https://pan.baidu.com/s/xxx 文件夹260723
260723：https://pan.baidu.com/s/xxx
提取码 260723
链接：https://pan.baidu.com/s/xxx
https://pan.baidu.com/s/xxx 260723
```

### Configuration Reference

The extraction code fallback uses existing configuration:
```python
# In .env or config
MESSAGE_DEFAULT_EXTRACTION_CODE=0409
```

This value is used when quant-format URLs lack the `?pwd=` parameter.