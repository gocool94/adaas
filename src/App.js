import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([]);
  const [userMessage, setUserMessage] = useState("");
  const [selectedModel, setSelectedModel] = useState("mistral-large");
  const [fileContent, setFileContent] = useState("");
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null); // Reference for the file input

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleInputChange = (e) => {
    setUserMessage(e.target.value);
  };

  const handleModelChange = (e) => {
    setSelectedModel(e.target.value);
  };

  const renderMessageContent = (content) => {
    // Split the content by newline characters and map each line to a <p> tag
    return content.split('\n').map((line, index) => (
      <p key={index}>{line}</p>  // Render each line as a new paragraph
    ));
  };
  
  const handleSendMessage = async () => {
    if (!userMessage.trim() && !fileContent.trim()) return;
  
    const newMessages = [
      ...messages,
      { role: "user", content: userMessage || "File Content: " + fileContent },
    ];
    setMessages(newMessages);
    setUserMessage("");
    setFileContent(""); // Clear file content after sending
  
    try {
      const response = await axios.post(
        "http://localhost:8000/query",
        {
          chat: userMessage,
          model: selectedModel,
          file: fileContent, // Send file content if provided
        },
        {
          headers: { "Content-Type": "application/json" },
        }
      );
  
      // Loop through the responses
      const responses = response.data;
  
      if (responses.length > 0) {
        // Map through the responses and accumulate the chat messages
        const newAssistantMessages = responses.map((responseItem) => {
          const { answer, context, current_bucket, next_bucket } = responseItem;
  
          return [
            { role: "assistant", content: renderMessageContent(JSON.stringify(answer, null, 2)) }, 
            { role: "assistant", content: renderMessageContent(`Context: ${context}`) },
            { role: "assistant", content: renderMessageContent(`Current Bucket: ${current_bucket}`) },
            { role: "assistant", content: renderMessageContent(`Next Bucket: ${next_bucket}`) },
          ];
        });
  
        // Flatten the array of messages and add them to the chat
        setMessages([
          ...newMessages,
          ...newAssistantMessages.flat(),  // Flatten to get a single array of messages
        ]);
      } else {
        setMessages([
          ...newMessages,
          { role: "assistant", content: "No relevant data found." },
        ]);
      }
    } catch (error) {
      console.error("Error while fetching response:", error);
      const errorMessage =
        error.response?.data?.detail || "An error occurred while processing.";
      setMessages([
        ...newMessages,
        { role: "assistant", content: errorMessage },
      ]);
    }
  };

  // Handle file upload and read content
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file && file.type === "text/plain") {
      const reader = new FileReader();
      reader.onload = () => {
        setFileContent(reader.result); // Store the content of the file
      };
      reader.readAsText(file);
    } else {
      alert("Please upload a valid text file.");
    }
  };

  return (
    <div className="App">
      <div className="title-container">
        <h1 className="animated-title">💰 ADAAS: Customer Q&A Advisory Assistant 💰</h1>
      </div>
      <div className="chat-container">
        <div className="messages">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`message ${message.role}`}
            >
              <p>{message.content}</p>
            </div>
          ))}
          <div ref={messagesEndRef}></div>
        </div>

        <div className="settings">
          <label htmlFor="model-select">Choose Model: </label>
          <select
            id="model-select"
            value={selectedModel}
            onChange={handleModelChange}
          >
            <option value="mistral-large">Mistral Large</option>
            <option value="reka-flash">Reka Flash</option>
            <option value="llama2-70b-chat">Llama2-70B Chat</option>
            <option value="gemma-7b">Gemma 7B</option>
            <option value="mixtral-8x7b">Mixtral 8x7B</option>
            <option value="mistral-7b">Mistral 7B</option>
          </select>
        </div>

        <div className="input-area">
          <input
            type="text"
            value={userMessage}
            onChange={handleInputChange}
            placeholder="Type your question..."
            className="chat-input"
          />
          <button className="send-button" onClick={handleSendMessage}>
            Send
          </button>
          <label htmlFor="file-upload" className="file-upload-icon">
            <i className="fas fa-paperclip"></i> {/* FontAwesome paperclip icon */}
          </label>
          <input
            type="file"
            id="file-upload"
            accept=".txt"
            onChange={handleFileUpload}
            ref={fileInputRef}
            className="file-input"
          />
        </div>
      </div>
    </div>
  );
}

export default App;
