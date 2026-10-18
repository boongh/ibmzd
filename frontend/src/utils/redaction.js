// Keyword rules are stored as regex rules in a fixed format the form can read back:
// (?i)(?:longest keyword|...|shortest keyword), case insensitive, every keyword escaped
const KEYWORDS_PREFIX = '(?i)(?:'
const KEYWORDS_SUFFIX = ')'
const SPECIAL = '\\^$.|?*+()[]{}/-'

export function escapeRegex(text) {
  return text.replace(/[\\^$.|?*+()[\]{}/-]/g, '\\$&')
}

export function keywordsToPattern(keywords) {
  const unique = [...new Set(keywords.map((keyword) => keyword.trim()).filter(Boolean))]
  unique.sort((a, b) => b.length - a.length) // longer keywords win when one contains another
  return KEYWORDS_PREFIX + unique.map(escapeRegex).join('|') + KEYWORDS_SUFFIX
}

// Keywords of a pattern made by keywordsToPattern, or null for any other regex
export function patternToKeywords(pattern) {
  if (!pattern.startsWith(KEYWORDS_PREFIX) || !pattern.endsWith(KEYWORDS_SUFFIX)) return null
  const body = pattern.slice(KEYWORDS_PREFIX.length, -KEYWORDS_SUFFIX.length)
  const keywords = []
  let current = ''
  for (let i = 0; i < body.length; i++) {
    const char = body[i]
    if (char === '\\') {
      if (!SPECIAL.includes(body[i + 1])) return null
      current += body[++i]
    } else if (char === '|') {
      keywords.push(current)
      current = ''
    } else if (SPECIAL.includes(char)) {
      return null
    } else {
      current += char
    }
  }
  keywords.push(current)
  return keywords.filter(Boolean)
}

export function normalizeLabel(label) {
  return label.trim().toUpperCase().replace(/\s+/g, '_')
}

// Same as the backend's restore: placeholders are matched case-insensitively, in one pass
export function restorePlaceholders(text, redactions) {
  if (!text || !redactions.length) return text
  const originals = new Map(redactions.map((r) => [r.placeholder.toUpperCase(), r.original]))
  const keys = [...originals.keys()].sort((a, b) => b.length - a.length)
  const pattern = new RegExp(keys.map(escapeRegex).join('|'), 'gi')
  return text.replace(pattern, (match) => originals.get(match.toUpperCase()) ?? match)
}

// While streaming, a placeholder can be split across chunks ("[EMA" + "IL_1]"): don't show the unfinished tail
export function withoutPartialPlaceholder(text) {
  const match = text.match(/\[[A-Za-z0-9_]{0,40}$/)
  return match ? text.slice(0, match.index) : text
}
