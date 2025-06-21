import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:catalog_app/models/brochure.dart';
import 'package:catalog_app/catalog_view.dart';

class CatalogSelectionScreen extends StatelessWidget {
  final String marketName;
  final List<Brochure> brochures;

  const CatalogSelectionScreen({
    super.key,
    required this.marketName,
    required this.brochures,
  });

  @override
  Widget build(BuildContext context) {
    // Sorts the brochures so 'current' appears before 'next'
    brochures.sort((a, b) => a.weekType.compareTo(b.weekType));

    return Scaffold(
      appBar: AppBar(
        title: Text('Select a catalog for ${marketName.toUpperCase()}'),
        centerTitle: true,
      ),
      body: ListView.builder(
        itemCount: brochures.length,
        itemBuilder: (context, index) {
          final brochure = brochures[index];
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
              subtitle: Text(brochure.validity),
              onTap: () {
                // This tap navigates to the final detail view
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => CatalogView(brochure: brochure),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}