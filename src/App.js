import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([]);
  const [userMessage, setUserMessage] = useState("");
  const [selectedModel, setSelectedModel] = useState("mistral-large");
  const [fileContent, setFileContent] = useState(""); // ✅ Store file content
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleInputChange = (e) => {
    setUserMessage(e.target.value);
  };

  const handleModelChange = (e) => {
    setSelectedModel(e.target.value);
  };

  // ✅ Read the selected file and store its content
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file && file.type === "text/plain") {
      const reader = new FileReader();
      reader.onload = () => {
        setFileContent(reader.result); // Store the file content
      };
      reader.readAsText(file);
    } else {
      alert("Please upload a valid text file.");
    }
  };

  const handleSendMessage = async () => {
    if (!userMessage.trim() && !fileContent.trim()) return;

    // Add user message and file content to chat
    const newMessages = [
      ...messages,
      { role: "user", content: userMessage || "File Content: " + fileContent },
    ];
    setMessages(newMessages);
    setUserMessage("");
    setFileContent(""); // Clear file content after sending

    try {
      const response = await axios.post(
        "http://localhost:8000/chat",  // ✅ API call to FastAPI backend
        {
          chat: userMessage,
          file: fileContent, // ✅ Send file content if provided
        },
        { headers: { "Content-Type": "application/json" } }
      );

      const responses = response.data;  // ✅ Get responses from API

      if (responses.length > 0) {
        // Format responses to show correctly in chat
        const formattedResponses = responses.map((responseItem) => ({
          role: "assistant",
          content: (
            <div className="p-4 bg-white shadow-md rounded-lg border-l-4 border-blue-500">
              {/* Domain Name */}
              <h2 className="text-xl font-bold text-gray-800 mb-2">
                🌎 Domain: <span className="text-blue-500">{responseItem.domain}</span>
              </h2>

              {/* Current Maturity Level */}
              <p className="text-lg font-semibold text-gray-600">
                📊 Current Maturity Level: <span className="text-green-500">{responseItem.maturity_level}</span>
              </p>

              {/* Next Maturity Level */}
              {responseItem.next_maturity_level && responseItem.next_maturity_level !== "Does not exist" && (
                <p className="text-lg font-semibold text-gray-700 mt-2">
                  🔄 Next Maturity Level:{" "}
                  <span className="text-red-500">{responseItem.next_maturity_level}</span>
                </p>
              )}

              {/* Answer */}
              <div className="mt-4 bg-gray-50 p-4 rounded-lg border-l-4 border-green-500">
                <p className="text-gray-800 text-base leading-relaxed font-medium">
                  <strong>💡 Answer:</strong> {responseItem.response}
                </p>
              </div>
            </div>
          ),
        }));

        setMessages([...newMessages, ...formattedResponses]);  // ✅ Update chat messages
      } else {
        setMessages([...newMessages, { role: "assistant", content: "No relevant data found." }]);
      }
    } catch (error) {
      console.error("Error while fetching response:", error);
      const errorMessage = error.response?.data?.detail || "An error occurred while processing.";
      setMessages([...newMessages, { role: "assistant", content: errorMessage }]);
    }
  };

  return (
    <div className="App p-6 bg-gray-100 min-h-screen">
      <div className="title-container">
        <h1 className="text-3xl font-bold text-center text-blue-600 mb-6">
          💰 ADAAS: Customer Q&A Advisory Assistant 💰
        </h1>
      </div>

      <div className="chat-container">
        <div className="messages space-y-4">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <p>{message.content}</p>
            </div>
          ))}
          <div ref={messagesEndRef}></div>
        </div>

        <div className="settings">
          <label htmlFor="model-select" className="font-semibold text-gray-700">Choose Model:</label>
          <select id="model-select" value={selectedModel} onChange={handleModelChange} className="ml-2 p-2 border rounded">
            <option value="mistral-large">Mistral Large</option>
            <option value="reka-flash">Reka Flash</option>
            <option value="llama2-70b-chat">Llama2-70B Chat</option>
            <option value="gemma-7b">Gemma 7B</option>
            <option value="mixtral-8x7b">Mixtral 8x7B</option>
            <option value="mistral-7b">Mistral 7B</option>
          </select>
        </div>

        <div className="input-area mt-4">
          <input
            type="text"
            value={userMessage}
            onChange={handleInputChange}
            placeholder="Type your question..."
            className="chat-input p-2 border rounded w-3/4"
          />
          <button className="send-button bg-blue-500 text-white px-4 py-2 rounded ml-2" onClick={handleSendMessage}>
            Send
          </button>
        </div>

        {/* ✅ File Upload Section */}
        <div className="file-upload mt-4">
          <input type="file" accept=".txt" onChange={handleFileUpload} className="hidden" id="file-upload" />
          <label htmlFor="file-upload" className="cursor-pointer bg-gray-200 p-2 rounded shadow-md">
            📂 Upload File
          </label>
          {fileContent && (
            <p className="text-sm text-gray-600 mt-2">
              ✅ File Loaded: {fileContent.substring(0, 50)}...
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
