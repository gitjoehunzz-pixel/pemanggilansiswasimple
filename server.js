/**
 * Server Pemanggilan Siswa SD Priangan Istiqamah
 * 
 * Multi-device: HP sebagai remote panggil, Komputer sebagai display + audio
 * Pakai Socket.IO untuk real-time sync antar device.
 */

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

app.use(express.static(__dirname));
app.use('/audio', express.static(path.join(__dirname, 'audio')));

// ==================== STATE ====================
const state = {
  queue: [],
  current: null,
  isPlaying: false,
  history: [],
  clients: {}  // socketId -> { type: 'display' | 'phone', name: '' }
};

// ==================== HELPERS ====================
function broadcastState() {
  io.emit('stateUpdate', {
    queue: state.queue,
    current: state.current,
    history: state.history.slice(-50),  // max 50 history
    isPlaying: state.isPlaying
  });
}

function getAudioFile(student) {
  const key = student.name.toLowerCase().replace(/ /g, '_').replace(/-/g, '_');
  return `audio/${student.code}_${key}.mp3`;
}

function addToHistory(student) {
  const time = new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const entry = { student, time, timestamp: Date.now() };
  state.history.push(entry);
  
  // Auto-clear after 3 hours
  setTimeout(() => {
    state.history = state.history.filter(h => h !== entry);
    broadcastState();
  }, 3 * 60 * 60 * 1000);
}

// ==================== QUEUE PROCESSOR ====================
async function processQueue() {
  if (state.isPlaying || state.queue.length === 0) return;
  
  state.isPlaying = true;
  state.current = state.queue.shift();
  broadcastState();
  
  // Notify all to play audio (2x)
  const audioPath = getAudioFile(state.current);
  io.emit('playAudio', { student: state.current, audioPath, repeat: 2 });
  
  // Wait for audio to finish (estimated ~3-5 seconds per play, 2x = ~8s)
  // We use a timeout as fallback; clients can also send 'audioDone'
  await new Promise(resolve => setTimeout(resolve, 8000));
  
  addToHistory(state.current);
  state.current = null;
  state.isPlaying = false;
  broadcastState();
  
  // Process next
  processQueue();
}

// ==================== SOCKET.IO ====================
io.on('connection', (socket) => {
  console.log(`🔗 Connected: ${socket.id}`);
  
  // Send current state to new client
  socket.emit('stateUpdate', {
    queue: state.queue,
    current: state.current,
    history: state.history.slice(-50),
    isPlaying: state.isPlaying
  });
  
  // Register client type
  socket.on('register', (data) => {
    state.clients[socket.id] = { type: data.type || 'phone', name: data.name || '' };
    const allClients = Object.entries(state.clients).map(([id, c]) => ({ id, ...c }));
    io.emit('clientsUpdate', allClients);
    console.log(`📱 ${socket.id} registered as ${data.type}`);
  });
  
  // Phone: call student
  socket.on('callStudent', (student) => {
    // Check if already in queue or current
    const inQueue = state.queue.some(s => s.name === student.name);
    const isCurrent = state.current && state.current.name === student.name;
    if (inQueue || isCurrent) return;
    
    state.queue.push(student);
    broadcastState();
    console.log(`📞 Called: ${student.name} (${student.cls}) | Queue: ${state.queue.length}`);
    
    if (!state.isPlaying) processQueue();
  });
  
  // Phone: remove from queue
  socket.on('removeFromQueue', (name) => {
    state.queue = state.queue.filter(s => s.name !== name);
    broadcastState();
  });
  
  // Phone: clear queue
  socket.on('clearQueue', () => {
    state.queue = [];
    state.current = null;
    state.isPlaying = false;
    broadcastState();
  });
  
  // Display: audio finished playing
  socket.on('audioDone', () => {
    // Audio confirmed done by display client
    // We still use the timeout, but this speeds things up
  });
  
  // Disconnect
  socket.on('disconnect', () => {
    delete state.clients[socket.id];
    io.emit('clientsUpdate', Object.entries(state.clients).map(([id, c]) => ({ id, ...c })));
    console.log(`❌ Disconnected: ${socket.id}`);
  });
});

// ==================== START ====================
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log('='.repeat(55));
  console.log('🔊 SERVER PEMANGGILAN SISWA');
  console.log('   SD Priangan Istiqamah');
  console.log('='.repeat(55));
  console.log(`   🌐 Server:  http://localhost:${PORT}`);
  console.log(`   🖥  Display: http://localhost:${PORT}/index.html`);
  console.log(`   📱 Phone:   http://localhost:${PORT}/panggil.html`);
  console.log('='.repeat(55));
});