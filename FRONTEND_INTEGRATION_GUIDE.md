# Frontend Integration Guide - Languages API

## Overview

This guide explains how to integrate the backend Languages API with the frontend language selector component. The API provides a dynamic list of available languages from the i18n system.

## Problem

Currently, the frontend uses a hardcoded list of languages. When new languages are added to the backend i18n system, they don't automatically appear in the frontend language selector.

## Solution

Use the `/api/languages` endpoint to fetch available languages dynamically.

## Backend API

### Endpoint: GET `/api/languages`

**Response:**
```json
{
  "type": "api/languages",
  "count": 3,
  "languages": ["en", "ko", "zh"]
}
```

**Details:** See [API_LANGUAGES.md](./API_LANGUAGES.md) for full documentation.

## Frontend Integration (i18next)

The frontend uses i18next for internationalization. Here's how to integrate the dynamic language API:

### Step 1: Fetch Available Languages

Create a utility function to fetch languages from the backend:

```typescript
// src/utils/languageApi.ts
export async function fetchAvailableLanguages(): Promise<string[]> {
  try {
    const response = await fetch('/api/languages');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.languages;
  } catch (error) {
    console.error('Error fetching languages:', error);
    // Fallback to default languages
    return ['en', 'zh'];
  }
}
```

### Step 2: Initialize i18next with Dynamic Languages

Update your i18next initialization to use the API:

```typescript
// src/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { fetchAvailableLanguages } from '../utils/languageApi';

export async function initializeI18n() {
  // Fetch available languages from backend
  const availableLanguages = await fetchAvailableLanguages();

  await i18n
    .use(initReactI18next)
    .init({
      // ... other config ...
      supportedLngs: availableLanguages,  // Use dynamic list
      fallbackLng: 'en',
      // ... other config ...
    });

  return i18n;
}
```

### Step 3: Update Language Selector Component

Modify your language selector to use the dynamic list:

```typescript
// src/components/LanguageSelector.tsx
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchAvailableLanguages } from '../utils/languageApi';

export const LanguageSelector: React.FC = () => {
  const { i18n } = useTranslation();
  const [languages, setLanguages] = useState<string[]>(['en', 'zh']); // Default fallback

  useEffect(() => {
    // Fetch available languages on component mount
    fetchAvailableLanguages().then(setLanguages);
  }, []);

  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  return (
    <select
      value={i18n.language}
      onChange={(e) => handleLanguageChange(e.target.value)}
    >
      {languages.map((lang) => (
        <option key={lang} value={lang}>
          {lang.toUpperCase()}
        </option>
      ))}
    </select>
  );
};
```

### Step 4: App Initialization

Update your app initialization to wait for i18n setup:

```typescript
// src/main.tsx or src/App.tsx
import { initializeI18n } from './i18n';

async function initApp() {
  // Initialize i18n with dynamic languages
  await initializeI18n();

  // Render app
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

initApp();
```

## Alternative: Simpler Integration

If you want a simpler approach without modifying i18next initialization:

```typescript
// Fetch languages and update selector only
export const LanguageSelector: React.FC = () => {
  const { i18n } = useTranslation();
  const [languages, setLanguages] = useState<string[]>([]);

  useEffect(() => {
    fetchAvailableLanguages().then((langs) => {
      setLanguages(langs);
      // Optionally update i18next supportedLngs
      i18n.options.supportedLngs = langs;
    });
  }, [i18n]);

  // ... rest of component
};
```

## Benefits

1. **Automatic Updates**: New languages appear automatically when added to backend
2. **No Frontend Changes**: Adding a new language only requires:
   - Creating translation JSON files in `src/open_llm_vtuber/locales/{lang}/`
   - No code changes needed!
3. **Centralized Management**: Single source of truth in the i18n system
4. **Consistent**: Backend and frontend always show the same languages

## Testing

### Test the API:
```bash
# Start the server
uv run run_server.py

# Test the endpoint
curl http://localhost:12393/api/languages
```

Expected output:
```json
{
  "type": "api/languages",
  "count": 3,
  "languages": ["en", "ko", "zh"]
}
```

### Test Frontend Integration:
1. Add a new language folder: `src/open_llm_vtuber/locales/ja/`
2. Add translation files to the new folder
3. Restart the server
4. Refresh the frontend
5. Check that Japanese (`ja`) appears in the language selector

## Migration Path

### Current State (Hardcoded):
```typescript
const languages = ['en', 'zh'];  // Hardcoded
```

### Target State (Dynamic):
```typescript
const languages = await fetchAvailableLanguages();  // Dynamic from API
```

### Rollout Steps:
1. ✅ Backend API implemented (`/api/languages`)
2. 🔄 Frontend integration (needs implementation)
3. 🔄 Testing and validation
4. 🔄 Deploy to production

## Repository Information

- **Frontend Repository**: https://github.com/Open-LLM-VTuber/Open-LLM-VTuber-Web
- **Backend Repository**: https://github.com/Open-LLM-VTuber/Open-LLM-VTuber
- **Frontend uses**: i18next for internationalization
- **Build branch**: `build` (contains compiled frontend)
- **Source branch**: `main` (contains source code)

## Next Steps

1. **Create an issue** in the [frontend repository](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber-Web/issues) requesting integration
2. **Or create a PR** with the changes outlined above
3. **Test thoroughly** with the backend API running

## Questions?

- See [API_LANGUAGES.md](./API_LANGUAGES.md) for API documentation
- Check frontend repository for current language selector implementation
- Refer to i18next documentation: https://www.i18next.com/

---

**Last Updated**: 2026-01-19
**Backend API Version**: v1.2.1+
**Status**: Backend implemented ✅ | Frontend integration pending 🔄
