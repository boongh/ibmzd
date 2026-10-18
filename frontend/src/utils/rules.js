import { PII_ENTITY_LABELS } from '../constants/piiEntities'
import { patternToKeywords } from './redaction'

// How a rule is shown in lists: { kind, summary, label }
export function describeRule(rule) {
  const config = rule.config
  if (config.type === 'ner') {
    return {
      kind: 'NER',
      summary: config.entities.map((entity) => PII_ENTITY_LABELS[entity] || entity).join(', '),
      label: 'By entity type',
    }
  }
  const keywords = patternToKeywords(config.pattern)
  return keywords
    ? { kind: 'Keywords', summary: keywords.join(', '), label: config.label }
    : { kind: 'Custom regex', summary: config.pattern, label: config.label }
}
