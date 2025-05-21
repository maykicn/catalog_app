// upload_brochures.js
const admin = require('firebase-admin');
const serviceAccount = require('./serviceAccountKey.json'); // Adını değiştirdiyseniz burayı güncelleyin
const brochuresData = require('./assets/data/brochures.json'); // JSON dosyanızın yolu

// Firebase Admin SDK'yı başlat
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
  // databaseURL: 'https://YOUR_PROJECT_ID.firebaseio.com' // Firestore için bu gerekli değil ama Realtime Database için gerekebilir
});

const db = admin.firestore();
const collectionName = 'brochures'; // Firestore'daki koleksiyonunuzun adı

async function uploadData() {
  console.log(`Starting upload to Firestore collection: ${collectionName}`);
  let uploadedCount = 0;

  for (const brochure of brochuresData) {
    try {
      // Her broşürü ayrı bir doküman olarak ekle
      // Firestore otomatik olarak bir doküman ID'si atar
      const docRef = await db.collection(collectionName).add(brochure);
      console.log(`Uploaded brochure with ID: ${docRef.id} - Title: ${brochure.title}`);
      uploadedCount++;
    } catch (error) {
      console.error(`Error uploading brochure ${brochure.title}:`, error);
    }
  }
  console.log(`Finished uploading. Total brochures uploaded: ${uploadedCount}`);
}

uploadData()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Overall upload error:", error);
    process.exit(1);
  });