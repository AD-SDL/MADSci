import { ref, watch, type Ref } from 'vue'

export function useStableValue<T>(source: () => T): Ref<T> {
  const stable = ref(source()) as Ref<T>
  watch(source, (next) => {
    if (JSON.stringify(next) !== JSON.stringify(stable.value)) {
      stable.value = next
    }
  })
  return stable
}
