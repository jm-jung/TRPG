import { useState, useEffect } from 'react'
import './App.css'
import ChatPanel from './component/Chat/ChatPanel'
import GameStatePanel from './component/GameState/GameStatePanel'
import UserInput from './component/UserInput/UserInput'
import Panel from './component/MainPanel/Panel'

function App() {
  const [gameState, setGameState] = useState({
    playerPersuasion: 0,
    demonLordResistance: 100,
    currentChapter: 1,
  })
  const [messages, setMessages] = useState([])

  useEffect(() => {
    // 게임 초기화 로직
    initializeGame()
  }, [])

  const initializeGame = async () => {
    try {

      const response = await fetch('/api/start-game', { method: 'POST' })
      const data = await response.json()
      setGameState(data.initialState)
    } catch (error) {
      console.error('게임 초기화 중 오류 발생:', error)
    }
  }

  const handleSendMessage = async (message) => {
    try {
      // TODO: 백엔드 API를 호출하여 메시지 전송 및 응답 받기
      // const response = await fetch('/api/send-message', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ message })
      // })
      // const data = await response.json()

      // 임시 로직: 실제 API 연동 전 테스트용
      const newPlayerMessage = { sender: 'player', content: message }
      const newDemonLordMessage = { sender: 'demonLord', content: '마왕의 대답...' }

      setMessages(prevMessages => [...prevMessages, newPlayerMessage, newDemonLordMessage])
      setGameState(prevState => ({
        ...prevState,
        playerPersuasion: prevState.playerPersuasion + 5,
        demonLordResistance: prevState.demonLordResistance - 5
      }))
    } catch (error) {
      console.error('메시지 전송 중 오류 발생:', error)
    }
  }

  return (
    <div className="app">
      <Panel>
        <GameStatePanel gameState={gameState} />
        <ChatPanel messages={messages} />
        <UserInput onSendMessage={handleSendMessage} />
      </Panel>
    </div>
  )
}

export default App