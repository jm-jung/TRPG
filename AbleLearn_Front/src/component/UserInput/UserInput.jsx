import 'react';
import './UserInput.css';
import { useCallback, useState } from 'react';

function UserInput({name}){
    const [typingMessage, setTypingMessage] = useState("");
    
    const handleChangeTypingMessage = useCallback((e) => {
        setTypingMessage(e.target.value);
    },[])

    const handleSendMessage = useCallback(() => {
        const noContent = typingMessage.trim() === "";

        if(noContent){return;}

        setTypingMessage("");
    }, [name, typingMessage]);

    return(
    <div className="UserInput">
        <input 
            className="TextBox"
            type="text" 
            placeholder='user input'
            value={typingMessage} 
            maxLength={400}
            onChange={handleChangeTypingMessage}
        ></input>
        <button 
            className="SubmitButton"
            onClick={handleSendMessage}
        >
            submit
        </button>
    </div>
    )
}

export default UserInput;