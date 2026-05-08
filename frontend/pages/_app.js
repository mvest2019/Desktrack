// pages/_app.js
// This wraps every page — perfect place for global CSS
import "../styles/globals.css";

export default function App({ Component, pageProps }) {
  return <Component {...pageProps} />;
}
