"""
Agent Messaging System for AI Development Pipeline
Redis-based pub/sub and queue system for agent-to-agent communication
"""

import redis
import json
import asyncio
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime
import uuid


class AgentMessage:
    """
    Standard message format for agent communication
    """
    
    def __init__(
        self,
        message_type: str,
        sender: str,
        recipient: str,
        content: Dict,
        priority: int = 2,
        message_id: Optional[str] = None
    ):
        """
        Initialize agent message
        
        Args:
            message_type: Type of message (task_assignment, status_update, etc.)
            sender: Agent sending the message
            recipient: Agent receiving the message (or "broadcast")
            content: Message content dictionary
            priority: Message priority (0=highest, 3=lowest)
            message_id: Optional unique message ID
        """
        self.message_id = message_id or str(uuid.uuid4())
        self.message_type = message_type
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.priority = priority
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert message to dictionary"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "priority": self.priority,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentMessage':
        """Create message from dictionary"""
        return cls(
            message_type=data["message_type"],
            sender=data["sender"],
            recipient=data["recipient"],
            content=data["content"],
            priority=data.get("priority", 2),
            message_id=data.get("message_id")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMessage':
        """Create message from JSON string"""
        return cls.from_dict(json.loads(json_str))


class AgentMessenger:
    """
    Messenger for agent-to-agent communication via Redis
    Supports both pub/sub and queue-based messaging
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        """
        Initialize agent messenger
        
        Args:
            agent_id: Unique identifier for this agent
            agent_type: Type of agent (product_manager, backend, etc.)
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        
        # Connect to Redis
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        
        # Pub/sub for real-time messaging
        self.pubsub = self.redis_client.pubsub()
        
        # Subscribe to agent-specific channel
        self.agent_channel = f"agent:{agent_type}:{agent_id}"
        self.pubsub.subscribe(self.agent_channel)
        
        # Also subscribe to broadcast channel
        self.pubsub.subscribe("agent:broadcast")
        
        # Message handlers
        self.message_handlers = {}
        
        # Running flag
        self.running = False
    
    async def send_message(
        self,
        recipient: str,
        message_type: str,
        content: Dict,
        priority: int = 2,
        use_queue: bool = False
    ) -> str:
        """
        Send a message to another agent
        
        Args:
            recipient: Recipient agent type or ID
            message_type: Type of message
            content: Message content
            priority: Message priority (0-3)
            use_queue: If True, use queue instead of pub/sub
        
        Returns:
            Message ID
        """
        # Create message
        message = AgentMessage(
            message_type=message_type,
            sender=f"{self.agent_type}:{self.agent_id}",
            recipient=recipient,
            content=content,
            priority=priority
        )
        
        if use_queue:
            # Add to queue with priority
            queue_name = f"queue:agent:{recipient}"
            self.redis_client.zadd(
                queue_name,
                {message.to_json(): priority}
            )
        else:
            # Publish to channel
            if recipient == "broadcast":
                channel = "agent:broadcast"
            else:
                channel = f"agent:{recipient}"
            
            self.redis_client.publish(channel, message.to_json())
        
        return message.message_id
    
    async def receive_message(self, timeout: int = 1) -> Optional[AgentMessage]:
        """
        Receive a message from pub/sub
        
        Args:
            timeout: Timeout in seconds
        
        Returns:
            AgentMessage or None if no message
        """
        message = self.pubsub.get_message(timeout=timeout)
        
        if message and message['type'] == 'message':
            try:
                return AgentMessage.from_json(message['data'])
            except Exception as e:
                print(f"Error parsing message: {e}")
                return None
        
        return None
    
    async def get_queued_message(self) -> Optional[AgentMessage]:
        """
        Get highest priority message from queue
        
        Returns:
            AgentMessage or None if queue empty
        """
        queue_name = f"queue:agent:{self.agent_type}:{self.agent_id}"
        
        # Get highest priority message (lowest score in sorted set)
        messages = self.redis_client.zrange(queue_name, 0, 0)
        
        if messages:
            message_json = messages[0]
            # Remove from queue
            self.redis_client.zrem(queue_name, message_json)
            
            return AgentMessage.from_json(message_json)
        
        return None
    
    def register_handler(
        self,
        message_type: str,
        handler: Callable[[AgentMessage], Any]
    ):
        """
        Register a handler for a specific message type
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self.message_handlers[message_type] = handler
    
    async def start_listening(self):
        """
        Start listening for messages and dispatch to handlers
        """
        self.running = True
        
        print(f"📡 {self.agent_type} ({self.agent_id}) started listening...")
        
        while self.running:
            # Check pub/sub messages
            message = await self.receive_message(timeout=1)
            
            if message:
                await self._handle_message(message)
            
            # Check queue messages
            queued_message = await self.get_queued_message()
            
            if queued_message:
                await self._handle_message(queued_message)
            
            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.1)
    
    async def _handle_message(self, message: AgentMessage):
        """Handle a received message"""
        print(f"📨 Received {message.message_type} from {message.sender}")
        
        # Find appropriate handler
        handler = self.message_handlers.get(message.message_type)
        
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                print(f"❌ Error handling message: {e}")
        else:
            print(f"⚠️  No handler for message type: {message.message_type}")
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.running = False
        self.pubsub.unsubscribe()
        print(f"🛑 {self.agent_type} ({self.agent_id}) stopped listening")
    
    async def broadcast(
        self,
        message_type: str,
        content: Dict,
        priority: int = 2
    ) -> str:
        """
        Broadcast a message to all agents
        
        Args:
            message_type: Type of message
            content: Message content
            priority: Message priority
        
        Returns:
            Message ID
        """
        return await self.send_message(
            recipient="broadcast",
            message_type=message_type,
            content=content,
            priority=priority,
            use_queue=False
        )
    
    async def request_assistance(
        self,
        from_agent: str,
        problem: str,
        context: Dict
    ) -> str:
        """
        Request assistance from another agent
        
        Args:
            from_agent: Agent to request help from
            problem: Description of the problem
            context: Additional context
        
        Returns:
            Message ID
        """
        return await self.send_message(
            recipient=from_agent,
            message_type="request_assistance",
            content={
                "problem": problem,
                "context": context
            },
            priority=1,  # High priority
            use_queue=True
        )
    
    async def send_status_update(
        self,
        status: str,
        details: Dict
    ) -> str:
        """
        Send a status update broadcast
        
        Args:
            status: Current status
            details: Status details
        
        Returns:
            Message ID
        """
        return await self.broadcast(
            message_type="status_update",
            content={
                "agent_type": self.agent_type,
                "agent_id": self.agent_id,
                "status": status,
                "details": details
            }
        )
    
    async def notify_completion(
        self,
        task_id: str,
        result: Dict,
        notify_agent: Optional[str] = None
    ) -> str:
        """
        Notify about task completion
        
        Args:
            task_id: ID of completed task
            result: Task result
            notify_agent: Specific agent to notify (or broadcast if None)
        
        Returns:
            Message ID
        """
        recipient = notify_agent or "broadcast"
        
        return await self.send_message(
            recipient=recipient,
            message_type="completion_notification",
            content={
                "task_id": task_id,
                "completed_by": f"{self.agent_type}:{self.agent_id}",
                "result": result
            },
            priority=1
        )
    
    def get_pending_message_count(self) -> int:
        """
        Get number of pending messages in queue
        
        Returns:
            Number of pending messages
        """
        queue_name = f"queue:agent:{self.agent_type}:{self.agent_id}"
        return self.redis_client.zcard(queue_name)
    
    def clear_queue(self):
        """Clear all pending messages in queue"""
        queue_name = f"queue:agent:{self.agent_type}:{self.agent_id}"
        self.redis_client.delete(queue_name)
    
    async def get_all_agent_statuses(self) -> List[Dict]:
        """
        Get status of all active agents
        
        Returns:
            List of agent status dictionaries
        """
        # This would query Redis for recent status updates
        # For now, return empty list
        return []


class MessageBus:
    """
    Central message bus for coordinating agent communication
    Used by Master Agent to monitor and coordinate
    """
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        """Initialize message bus"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe("agent:broadcast")
        
        # Track agent statuses
        self.agent_statuses = {}
    
    async def monitor_messages(self, duration: int = 60):
        """
        Monitor all agent messages for a duration
        
        Args:
            duration: Duration to monitor in seconds
        """
        print(f"👁️  Monitoring agent messages for {duration} seconds...")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < duration:
            message = self.pubsub.get_message(timeout=1)
            
            if message and message['type'] == 'message':
                try:
                    agent_message = AgentMessage.from_json(message['data'])
                    print(f"📡 [{agent_message.message_type}] "
                          f"{agent_message.sender} → {agent_message.recipient}")
                except Exception as e:
                    print(f"Error parsing message: {e}")
            
            await asyncio.sleep(0.1)
        
        print("✅ Monitoring complete")
    
    def get_queue_stats(self) -> Dict:
        """
        Get statistics about all message queues
        
        Returns:
            Dictionary with queue statistics
        """
        stats = {}
        
        # Get all queue keys
        queue_keys = self.redis_client.keys("queue:agent:*")
        
        for queue_key in queue_keys:
            count = self.redis_client.zcard(queue_key)
            stats[queue_key] = count
        
        return stats
    
    def clear_all_queues(self):
        """Clear all agent message queues"""
        queue_keys = self.redis_client.keys("queue:agent:*")
        
        for queue_key in queue_keys:
            self.redis_client.delete(queue_key)
        
        print(f"🧹 Cleared {len(queue_keys)} message queues")


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def create_messenger(agent_type: str, agent_id: str = None) -> AgentMessenger:
    """
    Create a messenger for an agent
    
    Args:
        agent_type: Type of agent
        agent_id: Optional specific agent ID (auto-generated if not provided)
    
    Returns:
        AgentMessenger instance
    """
    if not agent_id:
        agent_id = str(uuid.uuid4())[:8]
    
    return AgentMessenger(
        agent_id=agent_id,
        agent_type=agent_type
    )


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    async def example():
        # Create two agents
        backend_agent = create_messenger("backend", "backend_1")
        frontend_agent = create_messenger("frontend", "frontend_1")
        
        # Register handlers
        async def handle_task(message: AgentMessage):
            print(f"Backend received task: {message.content}")
        
        backend_agent.register_handler("task_assignment", handle_task)
        
        # Send a message
        await frontend_agent.send_message(
            recipient="backend:backend_1",
            message_type="task_assignment",
            content={"task": "Implement user API"},
            priority=1
        )
        
        # Backend processes message
        message = await backend_agent.receive_message()
        if message:
            await backend_agent._handle_message(message)
        
        print("Example complete!")
    
    # Run example
    asyncio.run(example())
