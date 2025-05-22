import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:catalog_app/models/brochure.dart'; // Yeni oluşturduğumuz Brochure modelini import ediyoruz
import 'package:catalog_app/catalog_view.dart'; // Katalog detaylarını göstereceğimiz sayfa

// Main screen widget that displays a list of brochures
class BrochureListScreen extends StatefulWidget {
  const BrochureListScreen({super.key});

  @override
  State<BrochureListScreen> createState() => _BrochureListScreenState();
}

class _BrochureListScreenState extends State<BrochureListScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Kataloglar'), // App bar title
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.location_on), // Location icon (Profital-like)
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Location feature coming soon!')),
              );
            },
          ),
        ],
      ),
      // StreamBuilder Firestore'dan gerçek zamanlı veri akışını dinler
      body: StreamBuilder<QuerySnapshot>(
        // 'brochures' koleksiyonundan verileri alıyoruz
        // .where('marketName', isEqualTo: 'lidl') ile sadece Lidl kataloglarını filtreliyoruz
        // .orderBy('timestamp', descending: true) ile en yeni katalogları en üste getiriyoruz
        stream: FirebaseFirestore.instance
            .collection('brochures')
            .where('marketName', isEqualTo: 'lidl') // Şimdilik sadece Lidl
            .orderBy('timestamp', descending: true)
            .snapshots(), // Gerçek zamanlı güncellemeler için snapshots()
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Hata: ${snapshot.error}'));
          }
          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return const Center(child: Text('Hiç katalog bulunamadı.'));
          }

          // Veri geldiğinde, dokümanları Brochure nesnelerine dönüştürüyoruz
          List<Brochure> brochures = snapshot.data!.docs
              .map((doc) => Brochure.fromFirestore(doc))
              .toList();

          return ListView.builder( // GridView yerine ListView kullanıyoruz (daha sonra değişebilir)
            itemCount: brochures.length,
            itemBuilder: (context, index) {
              Brochure brochure = brochures[index];
              return Card(
                margin: const EdgeInsets.all(8.0),
                child: ListTile(
                  leading: brochure.thumbnailUrl.isNotEmpty
                      ? Image.asset(
                          brochure.thumbnailUrl,
                          //assets/images/test.png',
                          width: 80,
                          height: 80,
                          fit: BoxFit.cover,
                          errorBuilder: (context, error, stackTrace) {
                            return const Icon(Icons.broken_image, size: 80); // Resim yüklenmezse
                          },
                        )
                      : const Icon(Icons.image_not_supported, size: 80),
                  title: Text(brochure.title),
                  subtitle: Text('${brochure.marketName.toUpperCase()} - ${brochure.validity}'),
                  onTap: () {
                    // Katalog detay sayfasına git (catalog_view.dart)
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => CatalogView(
                          // CatalogView'a title, validity ve images yerine tüm Brochure nesnesini gönderiyoruz
                          brochure: brochure, 
                        ),
                      ),
                    );
                  },
                ),
              );
            },
          );
        },
      ),
      // Bottom navigation bar, önceki kodunuzdaki ile aynı kaldı
      bottomNavigationBar: BottomNavigationBar(
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.favorite_border),
            label: 'Favorites',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.bookmark_border),
            label: 'Bookmarks',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.message),
            label: 'Messages',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
        selectedItemColor: Colors.red, // Color for the selected icon
        unselectedItemColor: Colors.grey, // Color for unselected icons
        type: BottomNavigationBarType.fixed, // Distributes items evenly
        onTap: (index) {
          // Placeholder for navigation logic (e.g., using a PageView for screens)
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Navigating to ${['Home', 'Favorites', 'Bookmarks', 'Messages', 'Profile'][index]}')),
          );
        },
      ),
    );
  }
}