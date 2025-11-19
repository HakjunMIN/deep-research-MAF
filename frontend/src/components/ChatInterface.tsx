/**
 * ChatInterface component - Main container for the research chat interface.
 */

import React, { useState } from "react";
import { InputBox } from "./InputBox";
import { MessageList } from "./MessageList";
import { useConversationStore } from "../store/conversationSlice";
import { apiClient } from "../services/api";
import { SearchSource } from "../types/message";

export const ChatInterface: React.FC = () => {
  const [inputDisabled, setInputDisabled] = useState(false);
  
  const messages = useConversationStore((state) => state.messages);
  const isLoading = useConversationStore((state) => state.isLoading);
  const error = useConversationStore((state) => state.error);
  
  const addMessage = useConversationStore((state) => state.addMessage);
  const setIsLoading = useConversationStore((state) => state.setIsLoading);
  const setError = useConversationStore((state) => state.setError);
  
  const handleSubmit = async (content: string, searchSources: SearchSource[]) => {
    if (inputDisabled) return;
    
    try {
      setInputDisabled(true);
      setIsLoading(true);
      setError(null);
      
      // Add query message to UI
      addMessage({
        id: `msg-${Date.now()}`,
        type: "query",
        content,
        timestamp: new Date().toISOString(),
      });
      
      // Submit research and wait for complete results
      const response = await apiClient.submitResearch(
        content,
        searchSources
      );
      
      // Add answer message to UI
      addMessage({
        id: `msg-${Date.now()}`,
        type: "answer",
        content: response.answer.content,
        timestamp: new Date().toISOString(),
        sources: response.answer.sources,
      });
      
    } catch (err) {
      console.error("Failed to submit research:", err);
      
      // Generate user-friendly error messages
      let errorMessage = "연구 요청이 실패했습니다. 다시 시도해주세요.";
      
      if (err instanceof Error) {
        if (err.message.includes("timeout") || err.message.includes("408")) {
          errorMessage = "요청 시간이 초과되었습니다. 네트워크 연결을 확인하고 다시 시도해주세요.";
        } else if (err.message.includes("Network") || err.message.includes("Failed to fetch")) {
          errorMessage = "서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.";
        } else if (err.message.includes("404")) {
          errorMessage = "요청한 리소스를 찾을 수 없습니다.";
        } else if (err.message.includes("500")) {
          errorMessage = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
        }
      }
      
      setError(errorMessage);
      
      addMessage({
        id: `msg-${Date.now()}`,
        type: "error",
        content: errorMessage,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setInputDisabled(false);
      setIsLoading(false);
    }
  };
  
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Deep Researcher
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                멀티에이전트 기반 심층 연구 어시스턴트
              </p>
            </div>
          </div>
        </header>
        
        {/* Message List */}
        <MessageList messages={messages} isLoading={isLoading} />
        
        {/* Error Display */}
        {error && (
          <div className="mx-4 mb-2 bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-red-800 text-sm">
            {error}
          </div>
        )}
        
        {/* Input Box */}
        <div className="border-t border-gray-200 bg-white p-4">
          <InputBox
            onSubmit={handleSubmit}
            isLoading={isLoading}
            disabled={inputDisabled}
            placeholder="연구 질문을 입력하세요..."
          />
        </div>
      </div>
    </div>
  );
};
