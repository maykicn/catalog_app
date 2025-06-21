import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:catalog_app/models/brochure.dart';
import 'package:catalog_app/catalog_view.dart';
import 'package:catalog_app/catalog_selection_screen.dart'; // <<< IMPORT NEW SCREEN

class BrochureListScreen extends StatefulWidget {
  const BrochureListScreen({super.key});

  @override
  State<BrochureListScreen> createState() => _BrochureListScreenState();
}

class _BrochureListScreenState extends State<BrochureListScreen> {
  String _selectedLanguage = 'de';

  Stream<QuerySnapshot> _buildStream() {
    return FirebaseFirestore.instance
        .collection('brochures')
        .where('language', isEqualTo: _selectedLanguage)
        .orderBy('marketName')
        .orderBy('weekType')
        .snapshots();
  }

  Map<String, List<Brochure>> _groupBrochures(List<Brochure> brochures) {
    final Map<String, List<Brochure>> grouped = {};
    for (final brochure in brochures) {
      if (grouped.containsKey(brochure.marketName)) {
        grouped[brochure.marketName]!.add(brochure);
      } else {
        grouped[brochure.marketName] = [brochure];
      }
    }
    return grouped;
  }

  // <<< NEW HELPER FUNCTION FOR TRANSLATIONS >>>
  String _getSubtitleForMultipleCatalogs(String languageCode) {
    switch (languageCode) {
      case 'de':
        return 'Aktuelle & kommende Angebote'; // German
      case 'fr':
        return 'Offres actuelles et à venir'; // French
      case 'it':
        return 'Offerte attuali e future'; // Italian
      default:
        return 'Current & upcoming offers'; // Fallback
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Catalogs'),
        centerTitle: true,
        actions: [
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
                const PopupMenuItem<String>(value: 'de', child: Text('Deutsch')),
                const PopupMenuItem<String>(value: 'fr', child: Text('Français')),
                const PopupMenuItem<String>(value: 'it', child: Text('Italiano')),
              ],
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
            return Center(child: Text('Error: ${snapshot.error}'));
          }
          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return const Center(child: Text('No catalogs found for this language.'));
          }

          final allBrochures = snapshot.data!.docs
              .map((doc) => Brochure.fromFirestore(doc))
              .toList();
          
          final groupedBrochures = _groupBrochures(allBrochures);
          final marketNames = groupedBrochures.keys.toList();

          return ListView.builder(
            itemCount: marketNames.length,
            itemBuilder: (context, index) {
              final marketName = marketNames[index];
              final marketBrochures = groupedBrochures[marketName]!;
              final previewBrochure = marketBrochures.first;

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
                    child: previewBrochure.thumbnail.isNotEmpty
                        ? CachedNetworkImage(
                            imageUrl: previewBrochure.thumbnail,
                            imageBuilder: (context, imageProvider) => Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(8),
                                image: DecorationImage(image: imageProvider, fit: BoxFit.cover),
                              ),
                            ),
                            placeholder: (context, url) => const Center(child: CircularProgressIndicator(strokeWidth: 2.0)),
                            errorWidget: (context, url, error) => const Icon(Icons.broken_image, size: 60),
                          )
                        : const Icon(Icons.image_not_supported, size: 60),
                  ),
                  title: Text(previewBrochure.marketName.toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  
                  subtitle: Text(
                    marketBrochures.length > 1
                        ? _getSubtitleForMultipleCatalogs(_selectedLanguage)
                        : previewBrochure.validity,
                    style: TextStyle(
                      fontSize: 12.5, // <<< THIS LINE MAKES THE FONT SMALLER
                      color: marketBrochures.length > 1 ? Colors.blue.shade700 : null,
                      fontWeight: marketBrochures.length > 1 ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                  
                  onTap: () {
                    if (marketBrochures.length == 1) {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => CatalogView(brochure: marketBrochures.first),
                        ),
                      );
                    } else {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => CatalogSelectionScreen(
                            marketName: marketName,
                            brochures: marketBrochures,
                          ),
                        ),
                      );
                    }
                  },
                ),
              );
            },
          );
        },
      ),
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