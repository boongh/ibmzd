<script setup>
import { computed, reactive, ref } from 'vue'
import { PII_ENTITY_GROUPS } from '../../constants/piiEntities'
import { keywordsToPattern, normalizeLabel, patternToKeywords } from '../../utils/redaction'
import FeedbackAlert from '../shared/FeedbackAlert.vue'

const props = defineProps({
  rule: { type: Object, default: null }, // null: create a new rule
  errorMessage: { type: String, default: '' },
})

const emit = defineEmits(['back', 'save', 'dismiss-error'])

const LABEL_SUGGESTIONS = ['PERSON', 'EMAIL', 'PHONE', 'ADDRESS', 'ORG', 'ID', 'PROJECT', 'CUSTOM']
const ALL_ENTITIES = PII_ENTITY_GROUPS.flatMap((group) => group.types.map(([entity]) => entity))

const config = props.rule?.config
const keywords = config?.type === 'regex' ? patternToKeywords(config.pattern) : null
// A regex rule that wasn't made from keywords: its pattern is shown but can't be edited here
const customPattern = config?.type === 'regex' && keywords === null ? config.pattern : null

const form = reactive({
  name: props.rule?.name || '',
  type: config?.type === 'ner' ? 'ner' : 'keywords',
  keywords: (keywords || []).join('\n'),
  label: config?.type === 'regex' ? config.label : '',
  // A new NER rule starts with every entity type selected
  entities: new Set(config?.type === 'ner' ? config.entities : ALL_ENTITIES),
})
const localError = ref('')

const keywordList = computed(() => form.keywords.split('\n').map((k) => k.trim()).filter(Boolean))

function toggleEntity(entity) {
  form.entities.has(entity) ? form.entities.delete(entity) : form.entities.add(entity)
}

function submit() {
  localError.value = ''
  const name = form.name.trim()
  if (form.type === 'ner') {
    if (!form.entities.size) return (localError.value = 'Select at least one entity type.')
    return emit('save', { name, config: { type: 'ner', entities: [...form.entities] } })
  }
  const label = normalizeLabel(form.label)
  if (!label) return (localError.value = 'Enter what the matches are replaced as, e.g. PERSON.')
  if (customPattern) return emit('save', { name, config: { type: 'regex', pattern: customPattern, label } })
  if (!keywordList.value.length) return (localError.value = 'Enter at least one keyword.')
  emit('save', { name, config: { type: 'regex', pattern: keywordsToPattern(keywordList.value), label } })
}
</script>

<template>
  <section class="secondary-page">
    <div class="page-back"><button class="back-link" @click="emit('back')">← Back to rules</button></div>
    <div class="page-heading-row">
      <div>
        <div class="eyebrow"><span class="eyebrow-dot"></span> PERSONAL PROTECTION</div>
        <h1>{{ rule ? 'Edit rule' : 'Create a rule' }}</h1>
        <p class="heading-description">Choose what the gateway should find and replace before a message is sent.</p>
      </div>
    </div>
    <FeedbackAlert v-if="errorMessage" heading="Rule was not saved" :message="errorMessage" @dismiss="emit('dismiss-error')" />
    <FeedbackAlert v-if="localError" :message="localError" @dismiss="localError = ''" />

    <form class="rule-form-card" @submit.prevent="submit">
      <label class="field-label">
        Rule name
        <input v-model="form.name" required maxlength="64" placeholder="e.g. Internal project names" />
      </label>

      <div v-if="!rule" class="choice-row" role="radiogroup" aria-label="Rule type">
        <label class="choice" :class="{ selected: form.type === 'keywords' }">
          <input v-model="form.type" type="radio" value="keywords" />
          <strong>Keywords</strong><small>Replace exact words or phrases you list.</small>
        </label>
        <label class="choice" :class="{ selected: form.type === 'ner' }">
          <input v-model="form.type" type="radio" value="ner" />
          <strong>NER</strong><small>Let the model find names, addresses, IDs and more.</small>
        </label>
      </div>

      <template v-if="form.type === 'keywords'">
        <label v-if="customPattern" class="field-label">
          Pattern
          <textarea :value="customPattern" rows="2" readonly></textarea>
          <small>This rule uses a custom regular expression and can't be edited as keywords.</small>
        </label>
        <label v-else class="field-label">
          Keywords to match
          <textarea v-model="form.keywords" rows="4" placeholder="Project Aurora&#10;Project Nova"></textarea>
          <small>One per line. Matching ignores upper / lower case.</small>
        </label>
        <label class="field-label">
          Replaced as
          <input v-model="form.label" list="label-suggestions" maxlength="32" placeholder="e.g. PROJECT" />
          <datalist id="label-suggestions">
            <option v-for="label in LABEL_SUGGESTIONS" :key="label" :value="label" />
          </datalist>
          <small>Matches become placeholders like [{{ normalizeLabel(form.label) || 'PROJECT' }}_1], so a short type name works best.</small>
        </label>
      </template>

      <div v-else class="entity-groups">
        <span class="field-label">Entity types to replace</span>
        <fieldset v-for="group in PII_ENTITY_GROUPS" :key="group.name" class="entity-group">
          <legend>{{ group.name }}</legend>
          <label v-for="[entity, label] in group.types" :key="entity" class="entity-option">
            <input type="checkbox" :checked="form.entities.has(entity)" @change="toggleEntity(entity)" />
            {{ label }}
          </label>
        </fieldset>
      </div>

      <div class="form-footer">
        <button class="secondary-button" type="button" @click="emit('back')">Cancel</button>
        <button class="primary-button" type="submit" :disabled="!form.name.trim()">Save rule <span>→</span></button>
      </div>
    </form>
  </section>
</template>
