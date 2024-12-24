# VSCode Azure ChatGPT

A Visual Studio Code extension that lets you chat with Azure OpenAI (ChatGPT) directly from your editor!

## Features

- **Chat Window**: Interact with Azure OpenAI’s ChatGPT in a Webview panel.
- **Customizable Settings**: Configure your Azure endpoint, API key, deployment name, and more in VS Code settings.
- **Easy to Use**: Just open the command palette and start chatting!

## Prerequisites

1. **Node.js** (v14+ recommended)
2. **npm** (bundled with Node.js) or **Yarn**
3. **Visual Studio Code** (v1.76.0 or later)
4. **Azure OpenAI** account with a deployed ChatGPT model (e.g. `gpt-3.5-turbo` or `gpt-4`)

## Installation & Setup

1. **Clone this repository**

   ```bash
   git clone https://github.com/<your-username>/<your-repo-name>.git
   ```

2. **Install dependencies**

   ```bash
   cd <your-repo-name>
   npm install
   ```

   > Or use Yarn: `yarn install`

3. **Open in Visual Studio Code**

   ```bash
   code .
   ```

4. **Set up your Azure OpenAI configuration**  
   In VS Code, go to **File > Preferences > Settings** (or **Code > Preferences > Settings** on macOS) and search for **Azure ChatGPT** (or open your `settings.json` directly).

   - `azureChatGPT.endpoint`: Your Azure OpenAI endpoint (e.g. `https://<YOUR-RESOURCE-NAME>.openai.azure.com/`)
   - `azureChatGPT.apiKey`: Your Azure OpenAI API Key
   - `azureChatGPT.deploymentName`: Your ChatGPT model deployment name
   - `azureChatGPT.apiVersion`: Azure API version (e.g. `2023-03-15-preview`)

   > **Note**: Store your API key securely if possible (e.g. Secret Storage). The above is for quick testing.

## Running & Using the Extension

1. **Launch the Extension**  
   Press `F5` in VS Code to open a new _Extension Development Host_ window running your extension.

2. **Open the Command Palette**

   - Keyboard shortcut:
     - Windows/Linux: `Ctrl + Shift + P`
     - macOS: `Cmd + Shift + P`
   - Type **“Azure ChatGPT”** and select **“Open Azure ChatGPT”**.

3. **Chat**
   - A webview panel titled “Azure ChatGPT” will appear.
   - Type your message or question, then click “Send.”
   - Watch for ChatGPT’s response!

## Packaging & Publishing (Optional)

- To create a `.vsix` file:

  ```bash
  npm run package
  ```

  This command uses [VSCE](https://code.visualstudio.com/api/working-with-extensions/publishing-extension) to bundle your extension into a package you can share or install manually.

- To publish directly to the Visual Studio Marketplace, you’ll need to set up a publisher and run:
  ```bash
  npm run publish
  ```

## Contributing

1. **Fork & Clone** this repo.
2. Create a new branch for your feature or fix.
3. Submit a Pull Request (PR) when ready for review.

## License

This project is licensed under the [MIT License](LICENSE).

---

Enjoy chatting with Azure OpenAI ChatGPT right inside VS Code! If you have any feedback or run into issues, feel free to open an [issue](https://github.com/<your-username>/<your-repo-name>/issues). Happy coding!
