import streamlit as st

def main():
    st.set_page_config(page_title="For My Love", page_icon="💖")
    
    st.title("🌹 You Are So Important To Me! 💕")
    st.write("""
    My love,
    
    I created this website just for you to remind you how much you mean to me. Every moment with you is special,
    and I never want you to feel unimportant. You are the most precious person in my life. ❤️
    """)
    
    st.image("https://source.unsplash.com/800x400/?love,couple", caption="You and Me Forever")
    
    st.header("💌 A Special Message")
    st.write("""
    From the moment I met you, my life has been filled with happiness. You bring joy, love, and endless smiles into my world.
    I cherish every second we spend together, and I promise to always make you feel as special as you are to me.
    """)
    
    st.subheader("📸 Our Beautiful Memories")
    image_paths = [
        "https://raw.githubusercontent.com/anshthakare16/pbl/main/IMG-20250307-WA0044.jpg",
        "https://raw.githubusercontent.com/anshthakare16/pbl/main/IMG-20250307-WA0043.jpg",
        "https://raw.githubusercontent.com/anshthakare16/pbl/main/IMG-20250307-WA0042.jpg",
        "https://raw.githubusercontent.com/anshthakare16/pbl/main/IMG-20250307-WA0041.jpg"
    ]
    
    if st.button("My Wifu 💖"):
        for path in image_paths:
            st.image(path, caption="Our Memory", use_container_width=True)
    
if __name__ == "__main__":
    main()
