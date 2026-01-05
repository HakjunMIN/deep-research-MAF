import type { ToolCall } from '../types';

interface ToolCallDisplayProps {
  toolCalls: ToolCall[];
}

export function ToolCallDisplay({ toolCalls }: ToolCallDisplayProps) {
  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  const getStatusIcon = (status: ToolCall['status']) => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'executing':
        return '🔄';
      case 'completed':
        return '✅';
      case 'error':
        return '❌';
      default:
        return '❓';
    }
  };

  const getStatusColor = (status: ToolCall['status']) => {
    switch (status) {
      case 'pending':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'executing':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getToolDisplayName = (name: string) => {
    const displayNames: Record<string, string> = {
      'search_google': 'Google Search',
      'search_arxiv': 'arXiv Search',
      'create_research_plan': 'Research Plan',
      'synthesize_answer': 'Answer Synthesis',
    };
    return displayNames[name] || name;
  };

  const getToolIcon = (name: string) => {
    const icons: Record<string, string> = {
      'search_google': '🔍',
      'search_arxiv': '📚',
      'create_research_plan': '📋',
      'synthesize_answer': '✍️',
    };
    return icons[name] || '🔧';
  };

  const parseArguments = (args: string | undefined) => {
    if (!args) return null;
    try {
      return JSON.parse(args);
    } catch {
      return args;
    }
  };

  const parseResult = (result: string | undefined) => {
    if (!result) return null;
    try {
      const parsed = JSON.parse(result);
      // For search results, show a summary
      if (parsed.results_count !== undefined) {
        return `Found ${parsed.results_count} results`;
      }
      if (parsed.keywords) {
        return `Keywords: ${parsed.keywords.join(', ')}`;
      }
      if (parsed.content) {
        return parsed.content.substring(0, 100) + '...';
      }
      return JSON.stringify(parsed, null, 2);
    } catch {
      return result;
    }
  };

  return (
    <div className="mt-3 space-y-2">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        🔧 Tool Calls
      </div>
      <div className="space-y-2">
        {toolCalls.map((toolCall) => (
          <div
            key={toolCall.id}
            className={`p-3 rounded-lg border ${getStatusColor(toolCall.status)}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">{getToolIcon(toolCall.name)}</span>
              <span className="font-medium text-sm">
                {getToolDisplayName(toolCall.name)}
              </span>
              <span className="ml-auto text-sm">
                {getStatusIcon(toolCall.status)}
              </span>
            </div>
            
            {toolCall.arguments && (
              <div className="mt-2">
                <div className="text-xs text-gray-500 mb-1">Arguments:</div>
                <pre className="text-xs bg-white/50 rounded p-2 overflow-x-auto">
                  {typeof parseArguments(toolCall.arguments) === 'object'
                    ? JSON.stringify(parseArguments(toolCall.arguments), null, 2)
                    : toolCall.arguments}
                </pre>
              </div>
            )}
            
            {toolCall.result && toolCall.status === 'completed' && (
              <div className="mt-2">
                <div className="text-xs text-gray-500 mb-1">Result:</div>
                <div className="text-xs bg-white/50 rounded p-2">
                  {parseResult(toolCall.result)}
                </div>
              </div>
            )}
            
            {toolCall.status === 'executing' && (
              <div className="mt-2 flex items-center gap-2 text-xs">
                <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Executing...</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
