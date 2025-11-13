# Architecture Documentation

## System Overview

This automation system implements a state machine-based approach to automatically clicking inline buttons in a Telegram bot. The system overcomes anti-automation protection that uses rapid message editing (2-15 times/second).

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    BotAutomation                        │
│                  (Main Orchestrator)                    │
└─────────────────────────────────────────────────────────┘
        │
        ├─── MessageMonitor ──────┐
        │                         │
        ├─── ButtonCache          │  Event Flow
        │                         │
        ├─── ButtonAnalyzer       ▼
        │                    New/Edit Event
        ├─── StabilizationDetector    │
        │                              ▼
        ├─── ClickExecutor        Process Message
        │                              │
        └─── StateMachine              ▼
                                  Check Trigger
                                       │
                                       ▼
                              ┌────────────────┐
                              │  IDLE State    │
                              └────────────────┘
                                       │
                                       ▼ (Trigger detected)
                              ┌────────────────┐
                              │  STEP_1 State  │
                              │  Click "Список"│
                              └────────────────┘
                                       │
                                       ▼ (Success)
                              ┌────────────────┐
                              │  STEP_2 State  │
                              │  Click first   │
                              └────────────────┘
                                       │
                                       ▼ (Success)
                              ┌────────────────┐
                              │  STEP_3 State  │
                              │  Click confirm │
                              └────────────────┘
                                       │
                                       ▼ (Success)
                              ┌────────────────┐
                              │  COMPLETED     │
                              └────────────────┘
                                       │
                                       ▼
                              ┌────────────────┐
                              │  IDLE          │
                              └────────────────┘
```

## Module Descriptions

### 1. MessageMonitor (FR-1.x)

**Purpose**: Monitor all messages and edits from target bot

**Responsibilities**:
- Listen for `NewMessage` and `MessageEdited` events
- Filter messages by bot ID
- Detect trigger messages
- Invoke callbacks for trigger and message events

**Key Methods**:
- `register_handlers()` - Register Telethon event handlers
- `_handle_message()` - Process incoming message/edit
- `_is_trigger_message()` - Check if message contains trigger text

**Event Flow**:
```
Telegram Event → MessageMonitor → ButtonCache.update_message()
                                → Check trigger
                                → Call on_trigger_callback()
```

### 2. ButtonCache (FR-MON-x)

**Purpose**: Cache recent messages with inline keyboards for fast access

**Data Structures**:
- `messages_cache: Dict[int, MessageData]` - Message cache by ID
- `buttons_history: List[Dict]` - History of button changes

**Responsibilities**:
- Store last N messages with buttons
- Track button changes across edits
- Provide fast button lookup by criteria
- Calculate edit frequency

**Key Methods**:
- `update_message()` - Update/add message to cache
- `find_button()` - Find button by criteria (text, position, keywords)
- `get_edit_frequency()` - Calculate message edit rate

### 3. ButtonAnalyzer (FR-2.x)

**Purpose**: Extract and analyze inline buttons from messages

**Responsibilities**:
- Parse `ReplyInlineMarkup` structures
- Extract button text and callback_data
- Search buttons by text/keywords/position
- Compare button structures

**Key Methods**:
- `extract_buttons()` - Extract all buttons from message
- `get_first_button()` - Get button at [0,0]
- `find_button_by_keywords()` - Search by keyword list
- `find_confirmation_button()` - Find confirmation button

**Button Search Criteria**:
- `"first"` - First button [0,0]
- `"text:Button Text"` - Exact text match
- `"contains:keyword"` - Text contains keyword
- `"position:row,col"` - Specific position
- `"keywords:word1,word2"` - Any keyword match

### 4. StabilizationDetector (FR-3.x)

**Purpose**: Detect when a message has stopped being edited

**Strategies**:

1. **Wait Strategy** (default):
   - Wait for `threshold` time (150ms) without edits
   - High reliability, minimal errors
   - Small delay acceptable

2. **Predict Strategy**:
   - Analyze edit patterns
   - Predict final state
   - Faster but more complex

3. **Aggressive Strategy**:
   - Minimal threshold (75ms)
   - Maximum speed
   - Higher error rate

**Key Methods**:
- `record_edit()` - Record message edit timestamp
- `is_stabilized()` - Check if message stabilized
- `wait_for_stabilization()` - Async wait for stabilization
- `get_stabilization_probability()` - Get probability (0-1)

**Edit History Tracking**:
```python
EditHistory:
  - edit_times: List[datetime]  # Last 20 edits
  - last_edit: datetime
  - get_edit_frequency() → float
  - get_average_interval() → float
```

### 5. ClickExecutor (FR-4.x)

**Purpose**: Execute button clicks with retry logic

**Responsibilities**:
- Send `GetBotCallbackAnswerRequest`
- Handle Telegram API errors
- Implement retry with exponential backoff
- Track click statistics

**Error Handling**:
- `MESSAGE_NOT_MODIFIED` → Retry with updated callback_data
- `QUERY_ID_INVALID` → Get fresh message, retry
- `FLOOD_WAIT` → Wait specified time, retry
- `TIMEOUT` → Retry with backoff

**Retry Logic**:
```python
for attempt in range(max_retries):
    try:
        result = GetBotCallbackAnswerRequest(...)
        return success
    except Error as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (attempt + 1))
            continue
        return failure
```

**Key Methods**:
- `click_button()` - Click with retry logic
- `click_button_info()` - Click using ButtonInfo
- `click_with_delay()` - Click after delay

### 6. StateMachine

**Purpose**: Manage automation workflow state transitions

**States**:
- `IDLE` - Waiting for trigger
- `STEP_1` - Clicking "Список прямых перевозок"
- `STEP_2` - Clicking first transport
- `STEP_3` - Clicking confirmation
- `COMPLETED` - Successfully finished
- `ERROR` - Error occurred

**State Data**:
- `current_state` - Current automation state
- `state_entered_at` - When entered current state
- `trigger_message_id` - ID of trigger message
- `step_X_message_id` - IDs for each step

**Timeouts**:
- Each step has configurable timeout
- `_timeout_checker()` monitors for exceeded timeouts
- Auto-reset on timeout

**Key Methods**:
- `transition_to()` - Transition to new state
- `start_automation()` - Begin automation (IDLE → STEP_1)
- `complete_step_X()` - Complete step and move to next
- `error()` - Transition to ERROR state
- `reset()` - Return to IDLE

### 7. BotAutomation (Main Orchestrator)

**Purpose**: Coordinate all modules to implement complete workflow

**Workflow**:

1. **Initialization**:
   ```python
   - Create all modules
   - Set up callbacks
   - Register event handlers
   ```

2. **Trigger Detection**:
   ```python
   _handle_trigger(message):
     - Check state is IDLE
     - Start state machine
     - Record edit
     - Schedule _execute_step_1()
   ```

3. **Step Execution**:
   ```python
   _execute_step_1(message_id):
     - Wait for stabilization
     - Get buttons from cache
     - Find target button
     - Click button
     - Wait for response

   _execute_step_2(message_id):
     - Similar to step 1
     - Click first button

   _execute_step_3(message_id):
     - Similar to step 1
     - Click confirmation
     - Complete automation
   ```

4. **Message Handling**:
   ```python
   _handle_message(message, is_edit):
     - Record edit
     - Check if new message (next step)
     - Transition to next state
   ```

**Key Features**:
- Async task coordination
- Timeout monitoring
- Statistics tracking
- Error recovery

## Data Flow

### Trigger Detection Flow

```
1. Bot sends message with trigger text
   ↓
2. MessageMonitor detects trigger
   ↓
3. Calls _handle_trigger()
   ↓
4. StateMachine → STEP_1
   ↓
5. Schedule _execute_step_1()
```

### Step Execution Flow

```
1. Wait for message stabilization
   - StabilizationDetector.wait_for_stabilization()
   ↓
2. Get message from cache
   - ButtonCache.get_message()
   ↓
3. Find target button
   - ButtonAnalyzer.find_button_by_keywords()
   ↓
4. Click button
   - ClickExecutor.click_button()
   ↓
5. Wait for response
   - New message triggers state transition
```

### Edit Tracking Flow

```
1. Bot edits message
   ↓
2. MessageMonitor receives edit event
   ↓
3. Update cache
   - ButtonCache.update_message()
   ↓
4. Record edit
   - StabilizationDetector.record_edit()
   ↓
5. Check stabilization
   - StabilizationDetector.is_stabilized()
```

## Performance Optimizations

### 1. Button Caching
- Cache last N messages with buttons
- Fast lookup by criteria
- No need to refetch messages

### 2. Async Processing
- All operations are async
- Parallel event processing
- Non-blocking waits

### 3. Minimal Delays
- 50ms after trigger
- 100ms between clicks
- 150ms stabilization threshold

### 4. Smart Retry
- Exponential backoff
- Max 3 retries
- Quick failure detection

## Configuration Points

All timing and behavior controlled via `config.py`:

```python
DELAY_AFTER_TRIGGER = 0.05      # 50ms
DELAY_BETWEEN_CLICKS = 0.1      # 100ms
STABILIZATION_THRESHOLD = 0.15  # 150ms
STABILIZATION_STRATEGY = 'wait'
MAX_RETRIES = 3
RETRY_DELAY = 0.1
```

## Error Recovery

### Automatic Recovery
- Retry on transient errors
- Fallback to first button if target not found
- Timeout detection with auto-reset

### Manual Recovery
- Reset to IDLE on error
- Clear caches
- Statistics preserved

## Monitoring

### Statistics Tracked
- Total/successful/failed runs
- Messages/edits/triggers count
- Clicks success rate
- Edit frequencies
- State transition times

### Logging
- All events logged
- Debug mode available
- Separate log file

## Extension Points

### Adding New Steps
1. Add state to `AutomationState` enum
2. Implement `_execute_step_X()` method
3. Update state transitions
4. Configure timeout

### Custom Button Finders
1. Extend `ButtonAnalyzer`
2. Add new search criteria
3. Update configuration keywords

### Alternative Strategies
1. Implement in `StabilizationDetector`
2. Add to strategy enum
3. Configure via `STABILIZATION_STRATEGY`
