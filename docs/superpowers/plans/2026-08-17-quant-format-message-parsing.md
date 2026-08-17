# Quant Format Message Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add support for quant-format Baidu Pan share link messages (quant-2026-3: https://pan.baidu.com/s/xxx?pwd=gqi4) while maintaining full backward compatibility with existing message formats.

**Architecture:** Priority-based pattern matching in existing MessageParser class - new quant pattern checked first, followed by existing 6-digit and link-only patterns. New helper method extracts pwd parameter from URLs.

**Tech Stack:** Python 3.8+, regex, pytest, existing MessageParser class structure

---

## File Structure

**Files to modify:**
- `src/feishu/message_parser.py` - Core parsing logic (add quant pattern, helper method, updated parse_message flow)
- `test/unit/test_message_parser.py` - Comprehensive unit tests for quant format

**No changes needed:**
- Database schema, other components, configuration files

---

## Task 1: Add QUANT_PATTERN regex constant

**Files:**
- Modify: `src/feishu/message_parser.py:21-35`

- [ ] **Step 1: Add new QUANT_PATTERN constant after COMBINED_PATTERN**

Find the COMBINED_PATTERN definition (around line 32) and add the new pattern immediately after it:

```python
# Quant格式：quant-{yyyy}-{m}: URL?pwd=xxx
# 匹配示例：
#   - quant-2026-3: https://pan.baidu.com/s/xxx?pwd=gqi4
#   - quant-2026-10: https://pan.baidu.com/s/xxx?pwd=abcd
#   - quant-2026-11: https://pan.baidu.com/s/xxx (pwd可选)
QUANT_PATTERN = re.compile(
    r'(quant-\d{4}-\d{1,2})\s*:\s*(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?)'
)
```

- [ ] **Step 2: Verify syntax and pattern validity**

Run: `python -c "from src.feishu.message_parser import MessageParser; parser = MessageParser(); print('QUANT_PATTERN defined:', hasattr(parser, 'QUANT_PATTERN'))"`
Expected: Output shows `QUANT_PATTERN defined: True`

- [ ] **Step 3: Commit**

```bash
git add src/feishu/message_parser.py
git commit -m "feat: add QUANT_PATTERN regex constant for quant-format messages"
```

---

## Task 2: Add extract_pwd_from_url helper method

**Files:**
- Modify: `src/feishu/message_parser.py:140-158`

- [ ] **Step 1: Add extract_pwd_from_url method after calculate_file_key method**

Find the `calculate_file_key` method (around line 159) and add the new helper method immediately before it:

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

- [ ] **Step 2: Test the method manually**

Run: `python -c "from src.feishu.message_parser import MessageParser; parser = MessageParser(); print('Test 1:', parser.extract_pwd_from_url('https://pan.baidu.com/s/xxx?pwd=gqi4')); print('Test 2:', parser.extract_pwd_from_url('https://pan.baidu.com/s/xxx'))"`
Expected: Output shows `Test 1: gqi4` and `Test 2: None`

- [ ] **Step 3: Commit**

```bash
git add src/feishu/message_parser.py
git commit -m "feat: add extract_pwd_from_url helper method for parsing extraction codes from URLs"
```

---

## Task 3: Add quant format parsing to parse_message method

**Files:**
- Modify: `src/feishu/message_parser.py:41-104`

- [ ] **Step 1: Add quant format parsing logic at the start of combined pattern checking**

Find the line `# 1. 尝试组合格式（同时有6位数字和链接，顺序不限）` (around line 78) and insert the new quant format parsing logic immediately before it:

```python
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
```

- [ ] **Step 2: Update comment numbers for existing parsing logic**

Change the existing comment `# 1. 尝试组合格式（同时有6位数字和链接，顺序不限）` to `# 2. 尝试组合格式（同时有6位数字和链接，顺序不限）` and change `# 2. 尝试纯链接格式（只有链接，没有目录名）` to `# 3. 尝试纯链接格式（只有链接，没有目录名）`

- [ ] **Step 3: Test basic parsing functionality**

Run: `python -c "from src.feishu.message_parser import MessageParser; parser = MessageParser(); result = parser.parse_message('quant-2026-3: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4'); print('Folder:', result.folder_name if result else None); print('Code:', result.extraction_code if result else None)"`
Expected: Output shows `Folder: quant-2026-3` and `Code: gqi4`

- [ ] **Step 4: Commit**

```bash
git add src/feishu/message_parser.py
git commit -m "feat: add quant format parsing logic with priority handling and validation"
```

---

## Task 4: Write comprehensive unit tests

**Files:**
- Modify: `test/unit/test_message_parser.py`

- [ ] **Step 1: Add test for quant format with pwd parameter**

Add this test at the end of the file:

```python
def test_parse_quant_format_with_pwd():
    """测试解析quant格式消息（包含pwd参数）"""
    parser = MessageParser()
    content = "quant-2026-3: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"
    result = parser.parse_message(content)
    
    assert result is not None
    assert result.folder_name == "quant-2026-3"
    assert result.extraction_code == "gqi4"
    assert result.share_link == "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"
    assert "quant-2026-3" in result.raw_content
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest test/unit/test_message_parser.py::test_parse_quant_format_with_pwd -v`
Expected: PASS

- [ ] **Step 3: Add test for quant format without pwd parameter**

```python
def test_parse_quant_format_without_pwd():
    """测试解析quant格式消息（不包含pwd参数，使用配置默认值）"""
    parser = MessageParser()
    content = "quant-2026-10: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA"
    result = parser.parse_message(content)
    
    assert result is not None
    assert result.folder_name == "quant-2026-10"  
    assert result.extraction_code == "0409"  # config default
    assert result.share_link == "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test/unit/test_message_parser.py::test_parse_quant_format_without_pwd -v`
Expected: PASS

- [ ] **Step 5: Add tests for various month formats**

```python
def test_parse_quant_format_different_months():
    """测试解析quant格式不同月份格式（单月份和双月份）"""
    parser = MessageParser()
    
    # Single digit month
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-3"
    
    # Double digit months
    result = parser.parse_message("quant-2026-10: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-10"
    
    result = parser.parse_message("quant-2026-11: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-11"
    
    result = parser.parse_message("quant-2026-12: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-12"
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest test/unit/test_message_parser.py::test_parse_quant_format_different_months -v`
Expected: PASS

- [ ] **Step 7: Add tests for rejection of other prefixes**

```python
def test_reject_other_prefixes():
    """测试拒绝其他前缀（research, report等）"""
    parser = MessageParser()
    
    # Wrong prefix - should be rejected
    result = parser.parse_message("research-2026-3: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None
    
    result = parser.parse_message("report-2026-11: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None
    
    result = parser.parse_message("data-2026-5: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest test/unit/test_message_parser.py::test_reject_other_prefixes -v`
Expected: PASS

- [ ] **Step 9: Add tests for invalid month rejection**

```python
def test_reject_invalid_months():
    """测试拒绝无效月份（0, 13等）"""
    parser = MessageParser()
    
    # Invalid months
    result = parser.parse_message("quant-2026-0: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None
    
    result = parser.parse_message("quant-2026-13: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None
    
    result = parser.parse_message("quant-2026-99: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None
```

- [ ] **Step 10: Run test to verify it passes**

Run: `pytest test/unit/test_message_parser.py::test_reject_invalid_months -v`
Expected: PASS

- [ ] **Step 11: Add tests for spacing variations**

```python
def test_quant_format_spacing_variations():
    """测试quant格式不同空格变体"""
    parser = MessageParser()
    
    # No spaces
    result = parser.parse_message("quant-2026-3:https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-3"
    
    # Spaces around colon
    result = parser.parse_message("quant-2026-3 : https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-3"
    
    # Multiple spaces
    result = parser.parse_message("quant-2026-3   :   https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-3"
```

- [ ] **Step 12: Run test to verify it passes**

Run: `pytest test/unit/test_message_parser.py::test_quant_format_spacing_variations -v`
Expected: PASS

- [ ] **Step 13: Add backward compatibility tests**

```python
def test_existing_formats_still_work():
    """测试现有格式仍然正常工作（向后兼容性）"""
    parser = MessageParser()
    
    # Combined format (6-digit + link)
    result = parser.parse_message("260723：https://pan.baidu.com/s/1abc123def456")
    assert result is not None
    assert result.folder_name == "260723"
    assert result.extraction_code == "0409"  # config default
    
    # Link-only format
    result = parser.parse_message("https://pan.baidu.com/s/1abc123def456")
    assert result is not None
    assert result.folder_name == "0409"  # config default
```

- [ ] **Step 14: Run test to verify it passes**

Run: `pytest test/unit/test_message_parser.py::test_existing_formats_still_work -v`
Expected: PASS

- [ ] **Step 15: Add message source preservation test**

```python
def test_quant_format_source_preservation():
    """测试quant格式消息来源保留"""
    parser = MessageParser()
    
    # Feishu source (default)
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result.source == "feishu"
    
    # DingTalk source
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc", source="dingtalk")
    assert result.source == "dingtalk"
```

- [ ] **Step 16: Run test to verify it passes**

Run: `pytest test/unit/test_message_parser.py::test_quant_format_source_preservation -v`
Expected: PASS

- [ ] **Step 17: Add URL extraction code parsing test**

```python
def test_extract_pwd_from_url():
    """测试从URL中提取提取码"""
    parser = MessageParser()
    
    # With ?pwd= parameter
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx?pwd=gqi4") == "gqi4"
    
    # With &pwd= parameter  
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx?foo=bar&pwd=abcd") == "abcd"
    
    # Without pwd parameter
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx") is None
    
    # Complex URL
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4&foo=bar") == "gqi4"
```

- [ ] **Step 18: Run all new tests to verify they pass**

Run: `pytest test/unit/test_message_parser.py -v`
Expected: All tests PASS (including existing tests)

- [ ] **Step 19: Commit**

```bash
git add test/unit/test_message_parser.py
git commit -m "test: add comprehensive unit tests for quant format message parsing"
```

---

## Task 5: Run full test suite and verify backward compatibility

**Files:**
- Test: `test/unit/test_message_parser.py`

- [ ] **Step 1: Run all message parser tests**

Run: `pytest test/unit/test_message_parser.py -v`
Expected: All tests PASS, no regressions

- [ ] **Step 2: Run broader unit test suite to ensure no side effects**

Run: `pytest test/unit/ -v`
Expected: All tests PASS

- [ ] **Step 3: Test with manual examples if desired**

Run: `python -c "
from src.feishu.message_parser import MessageParser
parser = MessageParser()

# Test quant format
result = parser.parse_message('quant-2026-3: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4')
print('Quant format - Folder:', result.folder_name, 'Code:', result.extraction_code)

# Test existing format
result = parser.parse_message('260723：https://pan.baidu.com/s/1abc123def456') 
print('Existing format - Folder:', result.folder_name, 'Code:', result.extraction_code)

# Test link-only format  
result = parser.parse_message('https://pan.baidu.com/s/1abc123def456')
print('Link-only format - Folder:', result.folder_name, 'Code:', result.extraction_code)
"`
Expected: All three formats parse correctly with appropriate folder names and extraction codes

- [ ] **Step 4: Final commit if any adjustments needed**

If any tests needed adjustments, commit the fixes:
```bash
git add src/feishu/message_parser.py test/unit/test_message_parser.py
git commit -m "fix: address edge cases in quant format parsing implementation"
```

---

## Task 6: Manual integration testing (optional but recommended)

**Files:**
- Test: Manual testing with actual system

- [ ] **Step 1: Start the application and test with real Feishu/DingTalk messages**

Run the main application and send test messages in the actual format to verify end-to-end functionality works correctly.

- [ ] **Step 2: Verify database logging with quant format folder names**

Check that messages with quant folder names are properly logged to the database with correct folder names.

- [ ] **Step 3: Verify file downloads work with quant format extraction codes**

Ensure that files from quant-format messages are successfully downloaded using the extracted pwd codes.

---

## Success Criteria

Implementation is successful when:
1. ✅ Quant format messages are correctly parsed and processed
2. ✅ Extraction codes from URLs are properly used for downloads  
3. ✅ Folder names with quant-style names are created correctly
4. ✅ All existing message formats continue to work unchanged
5. ✅ All unit tests pass (new and existing)
6. ✅ Manual testing confirms end-to-end functionality
7. ✅ No regression in existing functionality

---

## Summary

This implementation adds support for quant-format Baidu Pan messages (`quant-2026-3: https://...?pwd=gqi4`) using a priority-based pattern matching approach. The new format is checked first, followed by existing formats to maintain full backward compatibility. Comprehensive unit tests ensure the feature works correctly and doesn't break existing functionality.