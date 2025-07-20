# Project Libraries & Dependencies

This document lists all libraries used in the audioTranscription project, including backend (FastAPI) and frontend (React) stacks. Each entry includes a description, use case, and recommended stable version.

---

## Backend (Python)

| Library                | Stable Version | Description & Use Case                                                                 |
|------------------------|---------------|---------------------------------------------------------------------------------------|
| fastapi                | 0.110.0       | Web framework for building APIs quickly and efficiently. Used for all backend routes.  |
| uvicorn                | 0.29.0        | ASGI server for running FastAPI apps. Development and production server.               |
| python-jose            | 3.3.0         | JWT token encoding/decoding for authentication.                                       |
| passlib[bcrypt]        | 1.7.4         | Password hashing and verification. Used for secure user password storage.              |
| pymongo                | 4.7.2         | MongoDB client for database operations.                                                |
| python-dotenv          | 1.0.1         | Loads environment variables from .env files.                                           |
| pandas                 | 2.2.2         | Data analysis and manipulation, especially for CSV uploads and processing.             |
| numpy                  | 1.26.4        | Numerical operations, used in data processing and ML tasks.                            |
| spacy                  | 3.7.4         | Natural Language Processing (NLP) tasks.                                               |
| openai                 | 1.33.0        | Access to OpenAI LLM APIs for RAG/chatbot features.                                    |
| groq                   | 0.7.0         | Integration with Groq LLM APIs (if used).                                              |
| sentence-transformers  | 2.7.0         | Embedding generation for semantic search and RAG.                                      |
| qdrant-client          | 1.7.3         | Vector database client for semantic search and RAG.                                    |
| pydub                  | 0.25.1        | Audio file manipulation and conversion.                                                |
| audioop-lts            | 1.0.0         | Audio processing utilities.                                                            |
| demjson3               | 3.0.6         | Robust JSON parsing for edge cases.                                                    |
| python-docx            | 1.1.0         | Parsing and reading DOCX files.                                                        |
| PyPDF2                 | 3.0.1         | Parsing and reading PDF files.                                                         |
| openpyxl               | 3.1.2         | Parsing and reading Excel files.                                                       |
| chardet                | 5.2.0         | Character encoding detection for file uploads.                                         |
| langchain              | 0.1.20        | Framework for building LLM-powered applications.                                       |
| langchain-community    | 0.0.32        | Community integrations for LangChain.                                                  |

---

## Frontend (JavaScript/React)

| Library                | Stable Version | Description & Use Case                                                                 |
|------------------------|---------------|---------------------------------------------------------------------------------------|
| react                  | 19.1.0        | Core UI library for building frontend components.                                      |
| react-dom              | 19.1.0        | DOM bindings for React.                                                                |
| react-redux            | 9.2.0         | State management for React apps.                                                       |
| @reduxjs/toolkit       | 2.8.2         | Simplified Redux logic, RTK Query for API calls and cache.                             |
| react-router-dom       | 7.6.3         | Routing and navigation for React apps.                                                 |
| tailwindcss            | 4.1.11        | Utility-first CSS framework for rapid UI development.                                  |
| @tailwindcss/vite      | 4.1.11        | Tailwind integration for Vite.                                                         |
| vite                   | 7.0.0         | Fast frontend build tool and dev server.                                               |
| @mui/material          | 7.2.0         | Material UI component library.                                                         |
| @mui/x-data-grid       | 8.7.0         | Advanced data grid/table components.                                                   |
| @mui/x-date-pickers    | 8.7.0         | Date picker components for Material UI.                                                |
| @emotion/react         | 11.14.0       | CSS-in-JS styling for React.                                                           |
| @emotion/styled        | 11.14.1       | Styled components for React.                                                           |
| @headlessui/react      | 2.2.4         | Unstyled UI primitives for React.                                                      |
| @heroicons/react       | 2.2.0         | SVG icon set for React.                                                                |
| lucide-react           | 0.525.0       | Icon library for React.                                                                |
| framer-motion          | 12.23.0       | Animation library for React.                                                           |
| dayjs                  | 1.11.13       | Lightweight date library.                                                              |
| file-saver             | 2.0.5         | Save files from browser.                                                               |
| papaparse              | 5.5.3         | CSV parsing in browser.                                                                |
| xlsx                   | 0.18.5        | Excel file parsing in browser.                                                         |
| docx                   | 9.5.1         | DOCX file generation and parsing in browser.                                           |
| jspdf                  | 3.0.1         | PDF generation in browser.                                                             |
| jspdf-autotable        | 5.0.2         | Table support for jsPDF.                                                               |
| react-toastify         | 11.0.5        | Toast notifications for React.                                                         |

---

## Dev Dependencies

| Library                | Stable Version | Description & Use Case                                                                 |
|------------------------|---------------|---------------------------------------------------------------------------------------|
| eslint                 | 9.29.0        | Linting for JavaScript/React code.                                                    |
| @eslint/js             | 9.29.0        | ESLint rules for JS.                                                                  |
| eslint-plugin-react-hooks | 5.2.0      | ESLint plugin for React hooks.                                                        |
| eslint-plugin-react-refresh | 0.4.20   | ESLint plugin for React Fast Refresh.                                                 |
| @types/react           | 19.1.8        | TypeScript types for React.                                                           |
| @types/react-dom       | 19.1.6        | TypeScript types for React DOM.                                                       |
| @vitejs/plugin-react   | 4.5.2         | Vite plugin for React.                                                                |
| globals                | 16.2.0        | Global variable definitions for ESLint.                                               |

---

## Notes
- **Stable versions** are based on latest releases as of July 2025 and project compatibility.
- **Use cases** are based on actual usage in this project (API, UI, data, ML, file parsing, etc).
- **Security:** All authentication and password handling uses secure libraries (`python-jose`, `passlib[bcrypt]`).
- **Data:** All file parsing (CSV, DOCX, PDF, XLSX) uses robust, well-maintained libraries.
- **Frontend:** UI is built with React, Material UI, Tailwind, and Vite for modern, fast development.
- **Backend:** API is built with FastAPI, MongoDB, and modern NLP/ML libraries for RAG/chatbot features.

---

## How to Update
- To update a library, use `pip install <library>==<version>` for Python, or `npm install <library>@<version>` for JS.
- Always check compatibility before upgrading major versions.
- For production, pin exact versions in `requirements.txt` and `package.json`.

---

## License
All libraries used are open source and compatible with commercial use.
