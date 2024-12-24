import * as vscode from "vscode";
import axios from "axios";

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand(
    "azureChatGPT.startChat",
    async () => {
      // 1. Read configurations
      const config = vscode.workspace.getConfiguration("azureChatGPT");
      const endpoint = config.get<string>("endpoint", "");
      const apiKey = config.get<string>("apiKey", "");
      const deploymentName = config.get<string>("deploymentName", "");
      const apiVersion = config.get<string>("apiVersion", "2023-03-15-preview");

      if (!endpoint || !apiKey || !deploymentName) {
        vscode.window.showErrorMessage(
          "Please set your Azure OpenAI endpoint, apiKey, and deploymentName in settings.",
        );
        return;
      }

      // 2. Create and show a new Webview panel
      const panel = vscode.window.createWebviewPanel(
        "azureChatGPT",
        "Azure ChatGPT",
        vscode.ViewColumn.One,
        {
          enableScripts: true,
        },
      );

      // 3. Set an initial HTML for the panel
      panel.webview.html = getWebviewContent();

      // 4. Handle messages from the Webview
      panel.webview.onDidReceiveMessage(
        async (message) => {
          switch (message.type) {
            case "userMessage":
              {
                const userText = message.text;
                try {
                  // 4a. Send request to Azure OpenAI
                  const azureResponse = await chatWithAzureOpenAI(
                    endpoint,
                    apiKey,
                    deploymentName,
                    apiVersion,
                    userText,
                  );

                  // 4b. Send the Azure OpenAI reply back to Webview
                  panel.webview.postMessage({
                    type: "botResponse",
                    text: azureResponse,
                  });
                } catch (err: any) {
                  vscode.window.showErrorMessage(err.message || String(err));
                }
              }
              break;
          }
        },
        undefined,
        context.subscriptions,
      );
    },
  );

  context.subscriptions.push(disposable);
}

// This function calls Azure OpenAI's ChatGPT completion API
async function chatWithAzureOpenAI(
  endpoint: string,
  apiKey: string,
  deploymentName: string,
  apiVersion: string,
  userText: string,
): Promise<string> {
  const url = `${endpoint}openai/deployments/${deploymentName}/chat/completions?api-version=${apiVersion}`;

  // Minimal request body for ChatGPT
  const data = {
    messages: [
      {
        role: "user",
        content: userText,
      },
    ],
  };

  const headers = {
    "Content-Type": "application/json",
    "api-key": apiKey,
  };

  const response = await axios.post(url, data, { headers });
  const reply = response.data?.choices?.[0]?.message?.content || "No response";
  return reply;
}

function getWebviewContent(): string {
  // Basic HTML with a text input, a "Send" button, and an output area
  return /* html */ `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <style>
        body { font-family: sans-serif; padding: 10px; }
        #chat-container {
          display: flex;
          flex-direction: column;
          height: 80vh;
          border: 1px solid #ccc;
          padding: 10px;
          overflow-y: auto;
        }
        .user-message { color: blue; margin-bottom: 8px; }
        .bot-message { color: green; margin-bottom: 8px; }
        #input-container {
          margin-top: 10px;
          display: flex;
        }
        #user-input {
          flex: 1;
          margin-right: 10px;
        }
      </style>
    </head>
    <body>
      <h1>Azure ChatGPT</h1>
      <div id="chat-container"></div>
      <div id="input-container">
        <input id="user-input" type="text" placeholder="Type your message..." />
        <button id="send-button">Send</button>
      </div>
      <script>
        const vscode = acquireVsCodeApi();

        const chatContainer = document.getElementById('chat-container');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');

        // Send message to Extension when user clicks "Send"
        sendButton.addEventListener('click', () => {
          const text = userInput.value;
          if (text.trim().length > 0) {
            appendMessage('user-message', text);
            vscode.postMessage({ type: 'userMessage', text });
            userInput.value = '';
          }
        });

        // Listen for messages from the Extension
        window.addEventListener('message', (event) => {
          const message = event.data;
          if (message.type === 'botResponse') {
            appendMessage('bot-message', message.text);
          }
        });

        function appendMessage(cssClass, text) {
          const div = document.createElement('div');
          div.className = cssClass;
          div.textContent = text;
          chatContainer.appendChild(div);
          chatContainer.scrollTop = chatContainer.scrollHeight;
        }
      </script>
    </body>
    </html>
  `;
}

// this method is called when your extension is deactivated
export function deactivate() {}
