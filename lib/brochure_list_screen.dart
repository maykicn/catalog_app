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
        // Title translated to English
        title: const Text('Catalogs'),
        centerTitle: true,
        actions: [
          // =========================================================================================
          // !!! FANCY LANGUAGE BUTTON IMPLEMENTED HERE !!!
          // The generic globe icon has been replaced with a styled button that shows the
          // current language code (DE, FR, IT). Tapping this button opens the menu.
          // =========================================================================================
          Padding(
            padding: const EdgeInsets.only(right: 12.0),
            child: PopupMenuButton<String>(
              onSelected: (String languageCode) {
                setState(() {
                  _selectedLanguage = languageCode;
                });
                ScaffoldMessenger.of(context).hideCurrentSnackBar();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Language changed to ${languageCode.toUpperCase()}.'),
                    duration: const Duration(seconds: 2),
                  ),
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
              // This is the new button widget that replaces the old icon
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white70, width: 1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  _selectedLanguage.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
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
            // Error message translated to English
            return Center(child: Text('Error: ${snapshot.error}'));
          }
          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            // Empty state message translated to English
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
