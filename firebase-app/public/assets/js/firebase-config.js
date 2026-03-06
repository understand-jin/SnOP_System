/**
 * Firebase Configuration - snop-system project
 */
const firebaseConfig = {
  apiKey:            "AIzaSyDuw8wMtH0eqeOS9P-ckw4mraV0q9L3m7g",
  authDomain:        "snop-system.firebaseapp.com",
  projectId:         "snop-system",
  storageBucket:     "snop-system.firebasestorage.app",
  messagingSenderId: "712805208409",
  appId:             "1:712805208409:web:ffb8a4a6c8087afeb8fc48",
  measurementId:     "G-2QGTVCGW3V"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();
