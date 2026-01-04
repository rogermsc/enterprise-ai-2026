-- Initialize database for AI Platform
-- Enable required extensions

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- =============================================================================
-- Core Tables
-- =============================================================================

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    model VARCHAR(100) DEFAULT 'claude-3-5-sonnet-20241022',
    tools JSONB DEFAULT '[]'::jsonb,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_results JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tool executions audit log
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    parameters JSONB NOT NULL,
    result JSONB,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'completed', 'failed')),
    duration_ms INTEGER,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Knowledge Base Tables
-- =============================================================================

-- Documents table for RAG
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(500),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document chunks with embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI embedding dimension
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- =============================================================================
-- Policy Tables
-- =============================================================================

-- Policy rules
CREATE TABLE IF NOT EXISTS policy_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    resource_pattern VARCHAR(500) NOT NULL,
    action VARCHAR(100) NOT NULL,
    conditions JSONB DEFAULT '{}'::jsonb,
    priority INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Sample Data: Customer Support Agent
-- =============================================================================

-- Insert customer support agent
INSERT INTO agents (id, name, description, system_prompt, tools) VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Customer Support Agent',
    'An AI-powered customer support agent for handling common inquiries',
    E'You are a helpful customer support agent for Acme Corp.

Your responsibilities:
1. Answer questions about products and services
2. Help with account issues
3. Process returns and refunds (with approval)
4. Escalate complex issues to human agents

Guidelines:
- Be professional and empathetic
- Never share customer PII unnecessarily
- Always verify customer identity before account changes
- Use the knowledge base for accurate information

Available tools:
- search_knowledge_base: Search help articles and documentation
- lookup_order: Get order details by order ID
- create_ticket: Create a support ticket for escalation
- send_email: Send email to customer (requires approval)',
    '[
        {"name": "search_knowledge_base", "description": "Search help articles", "requires_approval": false},
        {"name": "lookup_order", "description": "Get order details", "requires_approval": false},
        {"name": "create_ticket", "description": "Create support ticket", "requires_approval": false},
        {"name": "send_email", "description": "Send email to customer", "requires_approval": true}
    ]'::jsonb
);

-- Insert sample knowledge base documents
INSERT INTO documents (id, title, content, source, metadata) VALUES
(
    'doc-001',
    'Return Policy',
    E'# Acme Corp Return Policy

## 30-Day Return Window
All products can be returned within 30 days of purchase for a full refund.

## Requirements
- Original packaging required
- Item must be unused and in original condition
- Proof of purchase (receipt or order number) required

## Process
1. Contact customer support to initiate return
2. Receive return shipping label via email
3. Ship item within 7 days
4. Refund processed within 5-7 business days after receipt

## Exceptions
- Digital products are non-refundable
- Customized items cannot be returned
- Clearance items are final sale',
    'internal-wiki',
    '{"category": "policies", "last_reviewed": "2024-01-01"}'::jsonb
),
(
    'doc-002',
    'Shipping Information',
    E'# Shipping Information

## Delivery Times
- Standard Shipping: 5-7 business days
- Express Shipping: 2-3 business days
- Overnight Shipping: Next business day

## Shipping Costs
- Orders over $50: Free standard shipping
- Standard: $5.99
- Express: $12.99
- Overnight: $24.99

## International Shipping
Available to select countries. Additional customs fees may apply.
Delivery time: 7-14 business days.

## Tracking
All orders include tracking. Check your confirmation email for tracking number.',
    'internal-wiki',
    '{"category": "shipping", "last_reviewed": "2024-01-15"}'::jsonb
),
(
    'doc-003',
    'Account Management',
    E'# Account Management

## Password Reset
1. Click "Forgot Password" on login page
2. Enter email address
3. Check email for reset link (expires in 24 hours)
4. Create new password (min 8 characters, 1 number, 1 special character)

## Update Email
1. Log into your account
2. Go to Settings > Profile
3. Enter new email address
4. Verify via confirmation email

## Close Account
Contact customer support to close your account. Note:
- Active subscriptions will be cancelled
- Order history will be retained for legal purposes
- Account cannot be recovered after 30 days',
    'internal-wiki',
    '{"category": "account", "last_reviewed": "2024-01-10"}'::jsonb
);

-- Insert policy rules
INSERT INTO policy_rules (name, resource_pattern, action, conditions, priority) VALUES
(
    'require_approval_for_email',
    'tool:send_email',
    'require_approval',
    '{"approvers": ["customer_success", "admin"]}'::jsonb,
    100
),
(
    'rate_limit_knowledge_search',
    'tool:search_knowledge_base',
    'rate_limit',
    '{"max_per_minute": 10}'::jsonb,
    50
),
(
    'log_all_tool_calls',
    'tool:*',
    'audit',
    '{"log_level": "info"}'::jsonb,
    0
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_tool_executions_session_id ON tool_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_status ON tool_executions(status);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);

-- =============================================================================
-- Functions
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aiplatform;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aiplatform;
