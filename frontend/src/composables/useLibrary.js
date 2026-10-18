import { ref } from 'vue'
import { api } from '../services/api'

// The user's rules, rulesets and LLM models: loaded once after login, refreshed after every change
export function useLibrary() {
  const rules = ref([])
  const rulesets = ref([])
  const models = ref([])
  const isLoading = ref(false)

  async function loadAll() {
    isLoading.value = true
    try {
      ;[rules.value, rulesets.value, models.value] = await Promise.all([
        api.rules.list(),
        api.rulesets.list(),
        api.models.list(),
      ])
    } finally {
      isLoading.value = false
    }
  }

  function resetAll() {
    rules.value = []
    rulesets.value = []
    models.value = []
  }

  // Rules show up inside rulesets, so a rule change also reloads the rulesets
  async function saveRule(id, body) {
    id ? await api.rules.update(id, body) : await api.rules.create(body)
    ;[rules.value, rulesets.value] = await Promise.all([api.rules.list(), api.rulesets.list()])
  }

  async function deleteRule(id) {
    await api.rules.remove(id)
    ;[rules.value, rulesets.value] = await Promise.all([api.rules.list(), api.rulesets.list()])
  }

  async function saveRuleset(id, body) {
    id ? await api.rulesets.update(id, body) : await api.rulesets.create(body)
    rulesets.value = await api.rulesets.list()
  }

  async function deleteRuleset(id) {
    await api.rulesets.remove(id)
    rulesets.value = await api.rulesets.list()
  }

  async function saveModel(id, body) {
    id ? await api.models.update(id, body) : await api.models.create(body)
    models.value = await api.models.list()
  }

  async function deleteModel(id) {
    await api.models.remove(id)
    models.value = await api.models.list()
  }

  return {
    rules,
    rulesets,
    models,
    isLoading,
    loadAll,
    resetAll,
    saveRule,
    deleteRule,
    saveRuleset,
    deleteRuleset,
    saveModel,
    deleteModel,
  }
}
