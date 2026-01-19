# Migration Guide: /api/languages API Changes

## Overview

The `/api/languages` API endpoint has been updated to provide richer language information including native display labels. This guide helps you migrate existing code that uses the old API format.

## What Changed

### Old Format (v1.0)

```json
{
  "type": "api/languages",
  "count": 3,
  "languages": ["en", "ko", "zh"]
}
```

**Usage:**
```javascript
const response = await fetch('/api/languages');
const data = await response.json();
const languages = data.languages;  // ["en", "ko", "zh"]

languages.forEach(lang => {
  console.log(lang);  // "en", "ko", "zh"
});
```

### New Format (v1.2+)

```json
{
  "type": "available_languages",
  "count": 3,
  "languages": [
    { "code": "en", "label": "English" },
    { "code": "ko", "label": "한국어" },
    { "code": "zh", "label": "中文" }
  ]
}
```

**Usage:**
```javascript
const response = await fetch('/api/languages');
const data = await response.json();
const languages = data.languages;  // [{code: "en", label: "English"}, ...]

languages.forEach(lang => {
  console.log(lang.code);   // "en", "ko", "zh"
  console.log(lang.label);  // "English", "한국어", "中文"
});
```

## Breaking Changes

### 1. Response Type Field

- **Old:** `type: "api/languages"`
- **New:** `type: "available_languages"`

**Migration:**
```javascript
// Old code (will break)
if (data.type === "api/languages") { ... }

// New code
if (data.type === "available_languages") { ... }
```

### 2. Languages Array Structure

- **Old:** Array of strings `["en", "ko", "zh"]`
- **New:** Array of objects `[{code: "en", label: "English"}, ...]`

**Migration Examples:**

#### Example 1: Populating a Language Selector

```javascript
// Old code (will break)
languages.forEach(lang => {
  const option = document.createElement('option');
  option.value = lang;              // lang is a string
  option.textContent = lang.toUpperCase();
  selector.appendChild(option);
});

// New code
languages.forEach(lang => {
  const option = document.createElement('option');
  option.value = lang.code;         // Use lang.code
  option.textContent = lang.label;  // Use native label
  selector.appendChild(option);
});
```

#### Example 2: Checking if a Language Exists

```javascript
// Old code (will break)
if (languages.includes('ko')) { ... }

// New code
if (languages.some(lang => lang.code === 'ko')) { ... }

// Or extract codes first
const codes = languages.map(lang => lang.code);
if (codes.includes('ko')) { ... }
```

#### Example 3: Getting First Language

```javascript
// Old code (will break)
const firstLang = languages[0];  // "en"

// New code
const firstLang = languages[0].code;  // "en"
const firstLabel = languages[0].label;  // "English"
```

#### Example 4: Filtering Languages

```javascript
// Old code (will break)
const filtered = languages.filter(lang => lang !== 'en');

// New code
const filtered = languages.filter(lang => lang.code !== 'en');
```

## Migration Strategies

### Strategy 1: Update Frontend Code (Recommended)

Update your frontend code to use the new format. This gives you access to native language labels.

**Benefits:**
- Better UX with native language names
- No additional mapping needed
- Future-proof

**Steps:**
1. Update fetch calls to handle new response structure
2. Change `lang` → `lang.code` everywhere
3. Use `lang.label` for display purposes

### Strategy 2: Add Adapter Layer (Temporary)

If immediate migration is not possible, add an adapter function:

```javascript
// Adapter function for backward compatibility
function adaptLanguagesResponse(data) {
  if (data.type === "available_languages") {
    // New format - extract codes only for old code
    return data.languages.map(lang => lang.code);
  }
  // Old format - return as is
  return data.languages;
}

// Usage
const response = await fetch('/api/languages');
const data = await response.json();
const languages = adaptLanguagesResponse(data);
// Now languages is ["en", "ko", "zh"] compatible with old code
```

**Note:** This is a temporary solution. Migrate to Strategy 1 as soon as possible.

## TypeScript Migration

### Old Type Definitions

```typescript
interface OldLanguagesResponse {
  type: "api/languages";
  count: number;
  languages: string[];
}
```

### New Type Definitions

```typescript
interface LanguageInfo {
  code: string;
  label: string;
}

interface LanguagesResponse {
  type: "available_languages";
  count: number;
  languages: LanguageInfo[];
}
```

### Migration

```typescript
// Old code
const fetchLanguages = async (): Promise<string[]> => {
  const response = await fetch('/api/languages');
  const data: OldLanguagesResponse = await response.json();
  return data.languages;
};

// New code
const fetchLanguages = async (): Promise<LanguageInfo[]> => {
  const response = await fetch('/api/languages');
  const data: LanguagesResponse = await response.json();
  return data.languages;
};

// Or if you only need codes
const fetchLanguageCodes = async (): Promise<string[]> => {
  const response = await fetch('/api/languages');
  const data: LanguagesResponse = await response.json();
  return data.languages.map(lang => lang.code);
};
```

## Testing Your Migration

### 1. Test API Response

```bash
curl http://localhost:12393/api/languages
```

Expected output:
```json
{
  "type": "available_languages",
  "count": 3,
  "languages": [
    {"code": "en", "label": "English"},
    {"code": "ko", "label": "한국어"},
    {"code": "zh", "label": "中文"}
  ]
}
```

### 2. Test Frontend Integration

Open your browser console and run:

```javascript
fetch('/api/languages')
  .then(r => r.json())
  .then(data => {
    console.log('Type:', data.type);
    console.log('Count:', data.count);
    console.log('Languages:', data.languages);
    data.languages.forEach(lang => {
      console.log(`  ${lang.code}: ${lang.label}`);
    });
  });
```

Expected output:
```
Type: available_languages
Count: 3
Languages: Array(3)
  en: English
  ko: 한국어
  zh: 中文
```

## Impact Assessment

### Low Impact (No Migration Needed)

- **New projects:** No impact, use new format from the start
- **Projects not using this API yet:** No impact

### Medium Impact (Simple Migration)

- **Projects using API for language codes only:** Simple mapping needed
  ```javascript
  const codes = data.languages.map(l => l.code);
  ```

### High Impact (Full Migration Needed)

- **Projects with hardcoded type checks:** Update type string
- **Projects treating languages as strings:** Update to object access
- **TypeScript projects:** Update type definitions

## Timeline

- **Current:** New API format is live (v1.2+)
- **Recommendation:** Migrate within 1-2 weeks
- **Support:** Old format is NOT supported (breaking change)

## Support

For questions or issues with migration:
1. Check [API_LANGUAGES.md](./API_LANGUAGES.md) for updated documentation
2. Check [FRONTEND_INTEGRATION_GUIDE.md](./FRONTEND_INTEGRATION_GUIDE.md) for integration examples
3. Open an issue on GitHub with `[migration]` tag

## Checklist

Use this checklist to ensure complete migration:

- [ ] Update API response type checks (`"api/languages"` → `"available_languages"`)
- [ ] Change `languages.forEach(lang => ...)` to use `lang.code`
- [ ] Update language existence checks (`includes('en')` → `some(l => l.code === 'en')`)
- [ ] Update TypeScript types if applicable
- [ ] Replace language display logic to use `lang.label`
- [ ] Test language selector functionality
- [ ] Test language switching
- [ ] Update unit tests if any
- [ ] Update integration tests if any

---

**Last Updated:** 2026-01-20
**API Version:** v1.2+
**Breaking Change:** Yes
