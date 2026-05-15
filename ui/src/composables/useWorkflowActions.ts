import { urls } from '@/store'

export interface WorkflowActionResult {
  success: boolean
  message: string
}

export function useWorkflowActions() {
  async function retryWorkflow(wfId: string, stepIndex: number): Promise<WorkflowActionResult> {
    try {
      const retryUrl = `${urls.value.workcell_server_url}workflow/${wfId}/retry?index=${stepIndex}`
      const response = await fetch(retryUrl, { method: 'POST' })
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return { success: true, message: `Retry from step ${stepIndex + 1} started` }
    } catch (error) {
      console.error('Error retrying workflow:', error)
      return { success: false, message: 'Failed to retry workflow' }
    }
  }

  async function resubmitWorkflow(wfId: string): Promise<WorkflowActionResult> {
    try {
      const resubmitUrl = `${urls.value.workcell_server_url}workflow/${wfId}/resubmit`
      const response = await fetch(resubmitUrl, { method: 'POST' })
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return { success: true, message: 'Workflow resubmitted successfully' }
    } catch (error) {
      console.error('Error resubmitting workflow:', error)
      return { success: false, message: 'Failed to resubmit workflow' }
    }
  }

  return {
    retryWorkflow,
    resubmitWorkflow,
  }
}
