# Diagram Generation Prompts for FinAgent Review-2 Document

Use these prompts with an AI image generator (DALL-E, Midjourney, or similar) to create the diagrams for the review document.

---

## 3.1 Design Concepts Architecture
**Filename:** `design_concepts_architecture.png`

**Prompt:**
```
Create a clean, professional technical architecture diagram showing a multi-agent AI system for financial advisory. The diagram should show:

- At the top: "User Query" box
- Center: "Orchestrator Agent" as the main coordinator
- Below that: 5 specialized agents in a row (Finance Agent, Code Agent, Knowledge Agent, Explainability Agent, Alert Agent)
- On the right side: "7-Layer MCP Context" stack showing layers (User Financial, Transactions, Goals, Knowledge, Working Memory, Audit, Alerts)
- At the bottom: "LLM (Gemini)" and "Data Stores (Redis, SQLite)"
- Arrows showing data flow between components

Style: Clean vector diagram, blue and white color scheme, professional technical documentation style, no 3D effects, minimal design
```

---

## 3.3 Conceptual Architecture
**Filename:** `conceptual_architecture.png`

**Prompt:**
```
Create a conceptual architecture diagram for a financial AI system showing three main tiers:

Top tier - "Presentation Layer":
- React Frontend box with icons for Chat, Dashboard, Alerts

Middle tier - "Application Layer":
- API Gateway
- Orchestrator
- 5 Agent boxes (Finance, Code, Knowledge, Explainability, Alert)
- Privacy Enhancer

Bottom tier - "Data Layer":
- Redis Cache
- SQLite Database
- Fi MCP (Banking Data)

Show arrows indicating data flow from top to bottom and responses going back up.

Style: Modern flat design, gradient blue-purple color scheme, clean lines, professional software architecture style
```

---

## 3.4.1 System Context Diagram
**Filename:** `system_context.png`

**Prompt:**
```
Create a system context diagram (C4 model style) showing:

Center: Large circle labeled "FinAgent System"

External entities around it:
- Top: "User" (stick figure) with bidirectional arrow labeled "Queries/Responses"
- Right: "Gemini LLM" (cloud shape) with arrow labeled "NLP Processing"
- Bottom-right: "Fi MCP Server" (server icon) with arrow labeled "Banking Data"
- Bottom: "Firecrawl" (web icon) with arrow labeled "Market Data"
- Left: "Redis" (database icon) with arrow labeled "Cache"

Style: Simple C4 diagram style, gray background, boxes with rounded corners, clear labels, professional documentation style
```

---

## 3.4.2 Data Flow Diagram Level 0
**Filename:** `dfd_level0.png`

**Prompt:**
```
Create a Data Flow Diagram (DFD) Level 0 showing:

External entity at top: "User" (rectangle)

Main process (circle): "FinAgent System"

Data stores (open rectangles on right):
- D1: User Context Store
- D2: Conversation History
- D3: Audit Log

Data flows (arrows with labels):
- User to Process: "Query"
- Process to User: "Response"
- Process to/from D1: "Read/Write Context"
- Process to/from D2: "Store Messages"
- Process to D3: "Log Actions"

External entity at bottom: "External APIs" with bidirectional "Data" flow

Style: Traditional DFD notation, black and white, clean lines, numbered processes and stores
```

---

## 3.4.3 Data Flow Diagram Level 1
**Filename:** `dfd_level1_query.png`

**Prompt:**
```
Create a Data Flow Diagram (DFD) Level 1 showing query processing:

Processes (circles numbered 1.1 to 1.5):
- 1.1: Validate Request
- 1.2: Load Context
- 1.3: Classify Intent
- 1.4: Route to Agents
- 1.5: Generate Response

Data stores:
- D1: MCP Context
- D2: Agent Registry

Data flows connecting all processes in sequence with labeled arrows:
- Query flows through validation to classification
- Context loaded from D1
- Agent selection based on intent
- Response generated and returned

Style: Standard DFD notation, horizontal layout, clear process numbering, black lines on white background
```

---

## 3.4.4 Sequence Diagram
**Filename:** `sequence_multi_agent.png`

**Prompt:**
```
Create a UML Sequence Diagram showing multi-agent query flow:

Participants (vertical lifelines):
- User (stick figure)
- React Frontend
- FastAPI Backend
- Orchestrator
- Finance Agent
- Explainability Agent
- LLM (Gemini)

Messages (horizontal arrows in sequence):
1. User -> Frontend: "Enter Query"
2. Frontend -> Backend: "POST /api/chat"
3. Backend -> Orchestrator: "process_query()"
4. Orchestrator -> Finance Agent: "analyze()"
5. Finance Agent -> LLM: "generate()"
6. LLM -> Finance Agent: "response"
7. Finance Agent -> Orchestrator: "result"
8. Orchestrator -> Explainability: "explain()"
9. Explainability -> Orchestrator: "explanation"
10. Orchestrator -> Backend: "final_response"
11. Backend -> Frontend: "JSON response"
12. Frontend -> User: "Display result"

Style: Clean UML sequence diagram, alternating colors for different actors, vertical dashed lines, activation boxes
```

---

## 3.4.5 Entity Relationship Diagram
**Filename:** `er_diagram.png`

**Prompt:**
```
Create an Entity Relationship Diagram (ERD) with Chen notation:

Entities (rectangles):
- User (id, email, createdAt)
- FinancialContext (id, income, expenses, assets, liabilities, goals)
- Conversation (id, title, createdAt)
- Message (id, role, content, timestamp)
- Alert (id, type, priority, status)
- AuditLog (id, action, details, timestamp)

Relationships (diamonds):
- User "has" FinancialContext (1:1)
- User "owns" Conversation (1:M)
- Conversation "contains" Message (1:M)
- User "receives" Alert (1:M)
- User "generates" AuditLog (1:M)

Style: Standard ERD notation, entities in rectangles, relationships in diamonds, cardinality notation (1, M), primary keys underlined
```

---

## 3.5 Layered Architecture
**Filename:** `layered_architecture.png`

**Prompt:**
```
Create a layered architecture diagram showing 4 horizontal layers stacked:

Layer 1 (Top) - "Presentation Layer":
- React Frontend, Voice Input, i18n Support

Layer 2 - "API Layer":
- FastAPI Routes, JWT Auth, Rate Limiter, CORS

Layer 3 - "Business Logic Layer":
- Orchestrator, Finance Agent, Code Agent, Knowledge Agent, Explainability Agent, Alert Agent

Layer 4 (Bottom) - "Data Access Layer":
- SQLAlchemy ORM, Redis Client, MCP Client

Each layer in a different shade of blue, getting darker towards bottom.
Vertical arrows showing dependencies only going downward.

Style: Clean layered diagram, horizontal bars for each layer, icons or small boxes for components within each layer, professional documentation style
```

---

## 4.2 Output Screens

### Dashboard Screen
**Filename:** `ui_dashboard.png`

**Prompt:**
```
Create a UI mockup of a financial dashboard web application:

- Dark theme with glassmorphism effects
- Header with "FinAgent" logo and navigation (Dashboard, Chat, Alerts, Settings)
- Left sidebar showing net worth summary card with value "₹45.2L"
- Main area with 4 cards:
  - "Monthly Income: ₹1.2L" with green indicator
  - "Monthly Expenses: ₹85K" with yellow indicator
  - "Savings Rate: 29%" with progress bar
  - "Goal Progress" with circular progress at 67%
- Right panel showing "Recent Transactions" list
- Bottom section with "Asset Allocation" pie chart

Style: Modern fintech UI, dark purple/blue gradient background, glassmorphism cards, Tailwind CSS inspired, professional and premium look
```

---

### Chat Screen
**Filename:** `ui_chat.png`

**Prompt:**
```
Create a UI mockup of an AI chat interface for financial advisory:

- Dark theme with gradient background
- Header: "AI Advisor" with voice input button (microphone icon)
- Left panel: Chat conversation with alternating user (blue) and AI (purple) message bubbles
- Sample messages:
  - User: "Should I invest in HDFC Bank?"
  - AI: "Based on your risk profile and current market conditions..." with reasoning steps shown
- Right panel: "Reasoning Chain" showing numbered steps of AI's analysis
- Bottom: Input field with "Ask a financial question..." placeholder and send button
- "Agents Used: Finance, Code, Knowledge" badge showing which agents processed the query

Style: Modern chat UI, dark theme, glassmorphism message bubbles, professional fintech aesthetic
```

---

### Alerts Screen
**Filename:** `ui_alerts.png`

**Prompt:**
```
Create a UI mockup of a financial alerts page:

- Dark theme consistent with fintech app
- Header: "Alerts & Insights" with filter dropdown
- List of alert cards, each showing:
  - Priority badge (HIGH in red, MEDIUM in yellow, LOW in green)
  - Alert title and description
  - Category tag (Portfolio, Goal, Market)
  - Action buttons (Acknowledge, Dismiss, Take Action)

Sample alerts:
- HIGH: "Portfolio Drift Detected - Equity allocation 8% above target"
- MEDIUM: "Emergency Fund Goal 75% Complete"
- LOW: "Monthly spending on track"

- Right panel: "Alert Statistics" with counts by category

Style: Modern notification UI, dark theme, color-coded priority badges, clean card layout
```

---

### Context Viewer Screen
**Filename:** `ui_context.png`

**Prompt:**
```
Create a UI mockup of a financial context viewer:

- Dark theme with sections for each MCP layer
- Header: "Your Financial Context"
- Expandable accordion sections:
  - "Financial Profile" showing income, expenses (values masked as HIGH/MEDIUM/LOW)
  - "Assets" showing list (Mutual Funds, FD, EPF)
  - "Liabilities" showing loans
  - "Goals" showing retirement, emergency fund, house purchase
  - "External Knowledge" showing connected data sources
- Privacy indicator icon showing "Privacy Mode: Active"
- Last updated timestamp

Style: Data-focused UI, dark theme, expandable sections, privacy-focused indicators, clean organized layout
```

---

### Agents Monitor Screen  
**Filename:** `ui_agents.png`

**Prompt:**
```
Create a UI mockup of an AI agents monitoring dashboard:

- Dark theme with technical/developer aesthetic
- Header: "Agents Monitor"
- Grid of 6 agent status cards:
  - Orchestrator: "Active" green status, "45 invocations"
  - Finance Reasoning: "Active" green, "38 invocations"
  - Code Agent: "Active" green, "12 invocations"
  - Knowledge Agent: "Active" green, "25 invocations"
  - Explainability: "Active" green, "45 invocations"
  - Alert Agent: "Idle" yellow, "5 invocations"
- Each card shows: Agent name, status indicator, invocation count, average latency
- Bottom: Performance graph showing agent response times over last hour

Style: Technical monitoring dashboard, dark theme with neon accents, status indicators, metrics cards
```

---

### Settings Screen
**Filename:** `ui_settings.png`

**Prompt:**
```
Create a UI mockup of an application settings page:

- Dark theme consistent with fintech app
- Header: "Settings"
- Sections with toggles and dropdowns:
  - "Language": Dropdown showing "English" with options (Hindi, Tamil, Telugu, Marathi)
  - "Theme": Toggle between Dark/Light mode
  - "Notifications": Toggles for different alert types
  - "Voice Input": Toggle to enable/disable
  - "Export Format": Radio buttons for CSV/PDF/Excel

Style: Clean settings UI, dark theme, organized sections, toggle switches, modern form elements
```

---

### Privacy & Audit Screen
**Filename:** `ui_privacy.png`

**Prompt:**
```
Create a UI mockup of a privacy and audit log screen:

- Dark theme with security-focused aesthetic
- Header: "Privacy & Audit"
- Top section: Privacy status cards
  - "Differential Privacy: ε=0.5" with shield icon
  - "Data Masking: Active" with lock icon
  - "Audit Trail: Hash-Verified" with checkmark
- Middle section: "Audit Log" table with columns:
  - Timestamp, Action, Details, Hash
  - Sample rows showing data access events
- Bottom section: "Data Control" buttons
  - "Request Data Export"
  - "Delete My Data"

Style: Security-focused UI, dark theme, trust indicators, audit table, action buttons
```

---

## Usage Instructions

1. Copy each prompt individually
2. Use with your preferred AI image generator (DALL-E 3, Midjourney, Stable Diffusion)
3. Save the generated image with the specified filename
4. Place all images in the `figures/` directory in your project
5. Compile the LaTeX document: `pdflatex review-2.tex`

**Recommended dimensions:** 1920x1080 or 1600x900 for screen mockups, 1200x800 for diagrams

**Alternative:** You can also create these diagrams manually using:
- Draw.io / diagrams.net (free, web-based)
- Lucidchart
- Figma (for UI mockups)
- PlantUML (for sequence diagrams)
- Mermaid.js (for flowcharts)
