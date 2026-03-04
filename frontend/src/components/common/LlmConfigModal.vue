<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getLlmConfig, updateLlmConfig } from '@/api/llmConfig'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()

const { t } = useI18n()

const providerName = ref('iFlow/通义千问')
const apiUrl = ref('')
const apiKey = ref('')
const model = ref('qwen3-max')
const saving = ref(false)
const showKey = ref(false)
const errorMsg = ref('')

watch(
  () => props.visible,
  async (val) => {
    if (!val) return
    errorMsg.value = ''
    try {
      const res = await getLlmConfig()
      const cfg = res.data.data
      providerName.value = cfg.providerName || 'iFlow/通义千问'
      apiUrl.value = cfg.apiUrl || ''
      apiKey.value = cfg.apiKey || ''
      model.value = cfg.model || 'qwen3-max'
    } catch {
      // keep defaults if config not yet saved
    }
  },
)

async function handleSave() {
  saving.value = true
  errorMsg.value = ''

  if (!apiUrl.value.trim()) {
    errorMsg.value = t('llmConfig.errorUrlRequired')
    saving.value = false
    return
  }
  try {
    new URL(apiUrl.value.trim())
  } catch {
    errorMsg.value = t('llmConfig.errorUrlInvalid')
    saving.value = false
    return
  }
  if (!apiKey.value.trim()) {
    errorMsg.value = t('llmConfig.errorKeyRequired')
    saving.value = false
    return
  }
  if (!model.value.trim()) {
    errorMsg.value = t('llmConfig.errorModelRequired')
    saving.value = false
    return
  }

  try {
    await updateLlmConfig({
      providerName: providerName.value,
      apiUrl: apiUrl.value,
      apiKey: apiKey.value,
      model: model.value,
    })
    emit('update:visible', false)
  } catch {
    errorMsg.value = t('llmConfig.saveFailed')
  } finally {
    saving.value = false
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="llm-modal-overlay" @click.self="close">
      <div class="llm-modal glass-card">
        <div class="llm-modal__header">
          <h3 class="llm-modal__title">{{ t('llmConfig.title') }}</h3>
          <button class="llm-modal__close" @click="close">&times;</button>
        </div>

        <div class="llm-modal__body">
          <label class="llm-modal__label">
            {{ t('llmConfig.providerName') }}
            <input v-model="providerName" class="llm-modal__input" />
          </label>

          <label class="llm-modal__label">
            {{ t('llmConfig.apiUrl') }}
            <input v-model="apiUrl" class="llm-modal__input" placeholder="https://..." />
          </label>

          <label class="llm-modal__label">
            {{ t('llmConfig.apiKey') }}
            <div class="llm-modal__key-row">
              <input
                v-model="apiKey"
                :type="showKey ? 'text' : 'password'"
                class="llm-modal__input llm-modal__input--key"
              />
              <button class="llm-modal__key-toggle" @click="showKey = !showKey">
                {{ showKey ? '&#9660;' : '&#9650;' }}
              </button>
            </div>
          </label>

          <label class="llm-modal__label">
            {{ t('llmConfig.model') }}
            <input v-model="model" class="llm-modal__input" />
          </label>

          <p v-if="errorMsg" class="llm-modal__error">{{ errorMsg }}</p>
        </div>

        <div class="llm-modal__footer">
          <button class="llm-modal__save" :disabled="saving" @click="handleSave">
            {{ saving ? t('llmConfig.saving') : t('llmConfig.save') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.llm-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.llm-modal {
  width: 420px;
  max-width: 90vw;
  padding: 24px;
  background: var(--bg-card);
  border: 1px solid var(--bg-card-border);
  border-radius: 16px;
  box-shadow: var(--glass-shadow);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
}

.llm-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.llm-modal__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.llm-modal__close {
  background: none;
  border: none;
  font-size: 20px;
  color: var(--text-secondary);
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}

.llm-modal__close:hover {
  color: var(--text-primary);
}

.llm-modal__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.llm-modal__label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.llm-modal__input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.llm-modal__input:focus {
  border-color: var(--accent-primary);
}

.llm-modal__key-row {
  display: flex;
  gap: 6px;
}

.llm-modal__input--key {
  flex: 1;
}

.llm-modal__key-toggle {
  padding: 8px 10px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--hover-bg);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 10px;
  transition: all 0.2s;
}

.llm-modal__key-toggle:hover {
  border-color: var(--accent-primary);
  color: var(--text-primary);
}

.llm-modal__error {
  color: var(--risk-high);
  font-size: 13px;
  margin: 0;
}

.llm-modal__footer {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.llm-modal__save {
  padding: 8px 24px;
  border: none;
  border-radius: 8px;
  background: var(--accent-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.llm-modal__save:hover {
  opacity: 0.9;
}

.llm-modal__save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
