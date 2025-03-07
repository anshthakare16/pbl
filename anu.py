import streamlit as st

def main():
    st.set_page_config(page_title="For My Love", page_icon="💖")
    
    st.title("🌹 You Are So Important To Me! 💕")
    st.write("""
    My love,
    
    You are my everything. Every moment with you is special,
    and I never want you to feel unimportant. You are the most precious person in my life. ❤️
    you are most beautiful thing that has ever happend to me.
    """)
    
    st.image("https://source.unsplash.com/800x400/?love,couple", caption="You and Me Forever")
    
    st.header("💌 A Special Message")
    st.write("""
    From the moment I met you, my life has been filled with happiness. You bring joy, love, and endless smiles into my world.
    I cherish every second we spend together, and I promise to always make you feel as special as you are to me.
    """)
    
    st.subheader("📸 Our Beautiful Memories")
    image_paths = [
        r"C:\Users\ANSH\Desktop\pabli\hmm\IMG-20250307-WA0041.jpg",
        r"C:\Users\ANSH\Desktop\pabli\hmm\IMG-20250307-WA0042.jpg",
        r"C:\Users\ANSH\Desktop\pabli\hmm\IMG-20250307-WA0043.jpg",
        r"C:\Users\ANSH\Desktop\pabli\hmm\IMG-20250307-WA0044.jpg"
    ]
    
    if st.button("My Wifu 💖"):
        for path in image_paths:
            st.image(path, caption="Our Memory", use_container_width=True)
    
if __name__ == "__main__":
    main()