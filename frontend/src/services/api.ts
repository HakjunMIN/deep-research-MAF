import type { StreamEvent, ResearchRequest, AGUIEvent, AGUIRequest } from '../types';

// Use relative URL for same-origin requests (no hardcoded localhost)
// This works for both development (with proxy) and production (same origin)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * AG-UI Protocol streaming client.
 * Connects to the AG-UI endpoint and streams responses using Server-Sent Events.
 */
export async function* streamAGUI(
  message: string,
  threadId?: string
): AsyncGenerator<AGUIEvent, void, unknown> {
  const request: AGUIRequest = {
    messages: [
      { role: 'system', content: 'You are a helpful deep research assistant. Use the available tools to research and provide comprehensive answers.' },
      { role: 'user', content: message },
    ],
  };

  if (threadId) {
    request.thread_id = threadId;
  }

  const response = await fetch(`${API_BASE_URL}/agui`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // Process complete SSE messages
      while (buffer.includes('\n\n')) {
        const splitIndex = buffer.indexOf('\n\n');
        const message = buffer.slice(0, splitIndex);
        buffer = buffer.slice(splitIndex + 2);
        
        if (message.startsWith('data: ')) {
          const data = message.slice(6); // Remove "data: " prefix
          
          try {
            const event = JSON.parse(data) as AGUIEvent;
            yield event;
          } catch (e) {
            console.error('Failed to parse AG-UI event:', data, e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Legacy streaming research endpoint.
 * @deprecated Use streamAGUI instead for AG-UI protocol support.
 */
export async function* streamResearch(
  request: ResearchRequest
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/research/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // Process complete SSE messages
      while (buffer.includes('\n\n')) {
        const splitIndex = buffer.indexOf('\n\n');
        const message = buffer.slice(0, splitIndex);
        buffer = buffer.slice(splitIndex + 2);
        
        if (message.startsWith('data: ')) {
          const data = message.slice(6); // Remove "data: " prefix
          
          try {
            const event = JSON.parse(data) as StreamEvent;
            yield event;
          } catch (e) {
            console.error('Failed to parse SSE event:', data, e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

