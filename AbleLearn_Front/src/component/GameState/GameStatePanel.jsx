import 'react'
import './GameStatePanel.css'

function GameStatePanel(){
    return(
        <div className="gameStatePanel">
            <div className="playerState">
                <div className="playerPronunciation">플레이어 설득력: </div>
                <div className="playerEmotion">플레이어 감정: </div>
            </div>
            <div className="enemyState">
                <div className="enemyResistance">마왕 저항력: </div>
                <div className="enemyEmotion">마왕 감정: </div>
            </div>
        </div>
    )
}

export default GameStatePanel