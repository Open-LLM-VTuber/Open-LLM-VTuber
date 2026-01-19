# Languages API Documentation

## Overview

The Languages API provides access to the list of available languages in the i18n system. This API dynamically returns all languages that have translation files in the `src/open_llm_vtuber/locales/` directory.

## Endpoint

### GET `/api/languages`

Returns a list of all available languages from the i18n system.

#### Request

```
GET /api/languages
```

No parameters required.

#### Response

**Success (200 OK)**

```json
{
  "type": "api/languages",
  "count": 3,
  "languages": ["en", "ko", "zh"]
}
```

**Error (500 Internal Server Error)**

```json
{
  "error": "Failed to get available languages"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Response type identifier: `"api/languages"` |
| `count` | integer | Number of available languages |
| `languages` | array of strings | List of language codes (e.g., `["en", "ko", "zh"]`) |

## Language Codes

The API returns ISO 639-1 language codes:

- `en` - English
- `zh` - Chinese (Simplified)
- `ko` - Korean

Additional languages can be added by creating new folders in `src/open_llm_vtuber/locales/` with the corresponding language code and translation JSON files.

## Usage Example

### JavaScript (Frontend)

```javascript
// Fetch available languages
fetch('/api/languages')
  .then(response => response.json())
  .then(data => {
    console.log('Available languages:', data.languages);
    // Use data.languages to populate language selector UI
    const languageSelector = document.getElementById('language-selector');
    data.languages.forEach(lang => {
      const option = document.createElement('option');
      option.value = lang;
      option.textContent = lang.toUpperCase();
      languageSelector.appendChild(option);
    });
  })
  .catch(error => console.error('Error fetching languages:', error));
```

### Python (Backend/Testing)

```python
import requests

response = requests.get('http://localhost:12393/api/languages')
if response.status_code == 200:
    data = response.json()
    print(f"Available languages: {data['languages']}")
else:
    print(f"Error: {response.status_code}")
```

### cURL

```bash
curl http://localhost:12393/api/languages
```

## Integration with Frontend

### Current State

The frontend currently uses a **hardcoded list** of languages. To integrate this API:

1. **Fetch languages on app initialization**:
   ```javascript
   const fetchLanguages = async () => {
     try {
       const response = await fetch('/api/languages');
       const data = await response.json();
       return data.languages;
     } catch (error) {
       console.error('Error fetching languages:', error);
       // Fallback to default languages
       return ['en', 'zh'];
     }
   };
   ```

2. **Update language selector component** to use the fetched list instead of hardcoded values

3. **Benefits**:
   - Automatically reflects new languages added to `locales/` directory
   - No frontend code changes needed when adding new languages
   - Centralized language management in the i18n system

## Adding New Languages

To add a new language and have it automatically appear in the API:

1. Create a new directory in `src/open_llm_vtuber/locales/` with the language code (e.g., `ja` for Japanese)
2. Add translation JSON files in that directory:
   - `character.json`
   - `system.json`
   - `upgrade.json`
   - `upgrade_compare.json`
   - `upgrade_merge.json`
   - `upgrade_routines.json`
3. The new language will automatically appear in `/api/languages` response
4. No code changes required!

## Related

- **I18n Manager**: `src/open_llm_vtuber/i18n_manager.py`
- **Translation Files**: `src/open_llm_vtuber/locales/{lang}/*.json`
- **Validation Script**: `validate_i18n_json.py` - Validates all translation files
- **Coverage Check**: `check_i18n_coverage.py` - Checks translation completeness

## Implementation Details

The API uses `I18nManager.get_available_languages()` which:
1. Scans the `locales/` directory for language folders
2. Returns all directory names as language codes
3. Automatically updates when new language folders are added
4. Requires no manual maintenance

## Notes

- The API response is cached by `I18nManager` for performance
- To reload languages after adding new ones, restart the server
- Language codes must be valid ISO 639-1 codes
- Each language folder must contain at least one valid JSON translation file
