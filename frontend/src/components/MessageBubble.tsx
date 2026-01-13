import type { Message } from '../types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { useState } from 'react';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [showAllSources, setShowAllSources] = useState(false);
  
  return (
    <div 
      className={`flex w-full animate-slide-up ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`flex gap-3 ${isUser ? 'max-w-3xl flex-row-reverse' : 'w-full flex-row'}`}>
        {/* Avatar */}
        <div 
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold text-sm ${
            isUser ? 'bg-gradient-to-br from-blue-500 to-blue-600' : 'bg-gradient-to-br from-purple-500 to-purple-600'
          }`}
        >
          {isUser ? 'U' : 'AI'}
        </div>
        
        {/* Message Content */}
        <div className={`flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'} ${isUser ? '' : 'flex-1'}`}>
          <div 
            className={`rounded-2xl px-4 py-3 ${isUser ? 'max-w-2xl' : 'max-w-5xl'} ${
              isUser 
                ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white' 
                : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
            }`}
          >
            <div className={`break-words prose prose-sm max-w-none ${isUser ? 'prose-invert' : ''}`}>
              {isUser ? (
                <div className="whitespace-pre-wrap">{message.content}</div>
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    // Custom styling for markdown elements
                    p: (props) => <p className="mb-2 last:mb-0" {...props} />,
                    ul: (props) => <ul className="mb-2 ml-4 list-disc" {...props} />,
                    ol: (props) => <ol className="mb-2 ml-4 list-decimal" {...props} />,
                    li: (props) => <li className="mb-1" {...props} />,
                    h1: (props) => <h1 className="text-xl font-bold mb-2 mt-4 first:mt-0" {...props} />,
                    h2: (props) => <h2 className="text-lg font-bold mb-2 mt-3 first:mt-0" {...props} />,
                    h3: (props) => <h3 className="text-base font-bold mb-2 mt-2 first:mt-0" {...props} />,
                    code: ({className, children, ...props}) => {
                      const match = /language-(\w+)/.exec(className || '');
                      return match ? (
                        <code className={className} {...props}>{children}</code>
                      ) : (
                        <code className="bg-gray-100 text-red-600 px-1 py-0.5 rounded text-sm" {...props}>
                          {children}
                        </code>
                      );
                    },
                    pre: (props) => (
                      <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto mb-2" {...props} />
                    ),
                    blockquote: (props) => (
                      <blockquote className="border-l-4 border-gray-300 pl-4 italic my-2" {...props} />
                    ),
                    a: (props) => (
                      <a className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
              {message.isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
              )}
            </div>
          </div>
          
          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className={`flex flex-col gap-1 text-xs text-gray-500 ${isUser ? 'max-w-2xl' : 'max-w-5xl'}`}>
              <span className="font-semibold">📚 Sources ({message.sources.length})</span>
              <div className="flex flex-col gap-1">
                {(showAllSources ? message.sources : message.sources.slice(0, 3)).map((source, idx) => (
                  <a
                    key={idx}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 hover:underline truncate"
                  >
                    {source.title}
                  </a>
                ))}
                {message.sources.length > 3 && (
                  <button
                    onClick={() => setShowAllSources(!showAllSources)}
                    className="text-blue-600 hover:text-blue-800 hover:underline text-left font-medium"
                  >
                    {showAllSources ? '▲ Show less' : `▼ Show all ${message.sources.length} sources`}
                  </button>
                )}
              </div>
            </div>
          )}
          
          {/* Timestamp */}
          <span className="text-xs text-gray-400">
            {message.timestamp.toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  );
}
