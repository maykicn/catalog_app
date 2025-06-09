import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:catalog_app/models/brochure.dart';
import 'package:catalog_app/catalog_view.dart';

class BrochureListScreen extends StatefulWidget {
  const BrochureListScreen({super.key});

  @override
  State<BrochureListScreen> createState() => _BrochureListScreenState();
}

class _BrochureListScreenState extends State<BrochureListScreen> {
  // State variable to hold the selected language, defaults to German.
  String _selectedLanguage = 'de';

  // Helper function to build the Firestore query dynamically based on language.
  Stream<QuerySnapshot> _buildStream() {
    return FirebaseFirestore.instance
        .collection('brochures')
        .where('language', isEqualTo: _selectedLanguage) // Filter by selected language
        .orderBy('timestamp', descending: true)
        .snapshots();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        // CHANGED: Title translated to English
        title: const Text('Catalogs'),
        centerTitle: true,
        actions: [
          // Language selection dropdown menu
          PopupMenuButton<String>(
            icon: const Icon(Icons.language),
            onSelected: (String languageCode) {
              setState(() {
                _selectedLanguage = languageCode;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                // CHANGED: SnackBar message translated to English
                SnackBar(content: Text('Language changed to ${languageCode.toUpperCase()}.')),
              );
            },
            itemBuilder: (BuildContext context) => <PopupMenuEntry<String>>[
              const PopupMenuItem<String>(
                value: 'de',
                child: Text('Deutsch'),
              ),
              const PopupMenuItem<String>(
                value: 'fr',
                child: Text('Français'),
              ),
              const PopupMenuItem<String>(
                value: 'it',
                child: Text('Italiano'),
              ),
            ],
          ),
        ],
      ),
      body: StreamBuilder<QuerySnapshot>(
        stream: _buildStream(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            // CHANGED: Error message translated to English
            return Center(child: Text('Error: ${snapshot.error}'));
          }
          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            // CHANGED: Empty state message translated to English
            return const Center(child: Text('No catalogs found for this language.'));
          }

          List<Brochure> brochures = snapshot.data!.docs
              .map((doc) => Brochure.fromFirestore(doc))
              .toList();

          return ListView.builder(
            itemCount: brochures.length,
            itemBuilder: (context, index) {
              Brochure brochure = brochures[index];
              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 6.0),
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                clipBehavior: Clip.antiAlias,
                child: ListTile(
                  contentPadding: const EdgeInsets.all(10.0),
                  leading: SizedBox(
                    width: 80,
                    height: 80,
                    child: brochure.thumbnail.isNotEmpty
                        ? CachedNetworkImage(
                            imageUrl: brochure.thumbnail,
                            imageBuilder: (context, imageProvider) => Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(8),
                                image: DecorationImage(
                                  image: imageProvider,
                                  fit: BoxFit.cover,
                                ),
                              ),
                            ),
                            placeholder: (context, url) => const Center(child: CircularProgressIndicator(strokeWidth: 2.0)),
                            errorWidget: (context, url, error) => const Icon(Icons.broken_image, size: 60),
                          )
                        : const Icon(Icons.image_not_supported, size: 60),
                  ),
                  title: Text(brochure.title, style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('${brochure.marketName.toUpperCase()} - ${brochure.validity}'),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => CatalogView(
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
      // Bottom navigation bar (unchanged)
      bottomNavigationBar: BottomNavigationBar(
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.favorite_border), label: 'Favorites'),
          BottomNavigationBarItem(icon: Icon(Icons.bookmark_border), label: 'Bookmarks'),
          BottomNavigationBarItem(icon: Icon(Icons.message), label: 'Messages'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profile'),
        ],
        selectedItemColor: Colors.red,
        unselectedItemColor: Colors.grey,
        type: BottomNavigationBarType.fixed,
        showUnselectedLabels: false,
        showSelectedLabels: false,
      ),
    );
  }
}
