import { ref } from 'vue'
import { urls } from '@/store'

export interface DatapointDisplayItem {
  key: string
  datapoint_id: string
  label: string
  data_type: string
  timestamp: string
}

export const data_headers = [
  { title: 'Label', key: 'label' },
  { title: 'Type', key: 'data_type' },
  { title: 'Timestamp', key: 'timestamp' },
  { title: 'Actions', key: 'actions' },
]

export function useDatapoints() {
  const loadingDatapoints = ref(false)
  const datapointMetadataCache = ref(new Map())

  function getDatapointDisplayItems(datapoints: any): DatapointDisplayItem[] {
    if (!datapoints) return []

    const items: DatapointDisplayItem[] = []

    for (const [key, value] of Object.entries(datapoints)) {
      if (typeof value === 'string') {
        const metadata = datapointMetadataCache.value.get(value)
        items.push({
          key,
          datapoint_id: value,
          label: metadata?.label || key,
          data_type: metadata?.data_type || 'unknown',
          timestamp: metadata?.data_timestamp ? new Date(metadata.data_timestamp).toLocaleString() : '',
        })

        if (!metadata) {
          fetchDatapointMetadata(value)
        }
      } else if (Array.isArray(value)) {
        value.forEach((id, index) => {
          if (typeof id === 'string') {
            const metadata = datapointMetadataCache.value.get(id)
            items.push({
              key: `${key}[${index}]`,
              datapoint_id: id,
              label: metadata?.label || `${key}[${index}]`,
              data_type: metadata?.data_type || 'unknown',
              timestamp: metadata?.data_timestamp ? new Date(metadata.data_timestamp).toLocaleString() : '',
            })

            if (!metadata) {
              fetchDatapointMetadata(id)
            }
          }
        })
      }
    }

    return items
  }

  async function fetchDatapointMetadata(datapointId: string) {
    try {
      loadingDatapoints.value = true
      const response = await fetch(`${urls.value["data_server_url"]}datapoint/${datapointId}`)
      if (response.ok) {
        const datapoint = await response.json()
        datapointMetadataCache.value.set(datapointId, {
          label: datapoint.label,
          data_type: datapoint.data_type,
          data_timestamp: datapoint.data_timestamp,
        })
      }
    } catch (error) {
      console.error(`Failed to fetch metadata for datapoint ${datapointId}:`, error)
    } finally {
      loadingDatapoints.value = false
    }
  }

  const forceFileDownload = (val: any, title: any) => {
    const url = window.URL.createObjectURL(new Blob([val]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', title)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  async function trydownload(id: string, label: string) {
    try {
      const response = await fetch(`${urls.value["data_server_url"]}datapoint/${id}/value`)
      if (response.ok) {
        const val = await response.blob()
        forceFileDownload(val, label || id)
      } else {
        console.error('Failed to download datapoint:', response.statusText)
      }
    } catch (error) {
      console.error('Error downloading datapoint:', error)
    }
  }

  async function showDatapointValue(id: string) {
    try {
      const response = await fetch(`${urls.value["data_server_url"]}datapoint/${id}/value`)
      if (response.ok) {
        const value = await response.json()
        alert(`Datapoint value: ${JSON.stringify(value, null, 2)}`)
      } else {
        console.error('Failed to fetch datapoint value:', response.statusText)
      }
    } catch (error) {
      console.error('Error fetching datapoint value:', error)
    }
  }

  return {
    loadingDatapoints,
    datapointMetadataCache,
    getDatapointDisplayItems,
    fetchDatapointMetadata,
    trydownload,
    showDatapointValue,
  }
}
