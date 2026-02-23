export function createReportSSE(
  alertId: number,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (e: Event) => void,
): EventSource {
  const url = `/api/report/${alertId}?stream=true`
  const es = new EventSource(url)
  es.onmessage = (e) => {
    if (e.data === '[DONE]') {
      onDone()
      es.close()
      return
    }
    try {
      const { token } = JSON.parse(e.data)
      onToken(token)
    } catch {
      // ignore malformed frames
    }
  }
  es.onerror = (e) => {
    onError(e)
    es.close()
  }
  return es
}
