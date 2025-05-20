import 'package:flutter/material.dart';
import 'package:catalog_app/brochure_list_screen.dart'; // Yeni oluşturduğumuz dosyayı import et

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Profital Clone MVP',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.red, // Consistent AppBar color
          foregroundColor: Colors.white,
        ),
      ),
      // Uygulamanın ana ekranı artık BrochureListScreen olacak
      home: const BrochureListScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

// CatalogView artık dışarıdan parametreler alacak şekilde güncellendi
class CatalogView extends StatefulWidget {
  final String catalogTitle;
  final String catalogValidity;
  final List<String> catalogImages;

  const CatalogView({
    super.key,
    required this.catalogTitle,
    required this.catalogValidity,
    required this.catalogImages,
  });

  @override
  _CatalogViewState createState() => _CatalogViewState();
}

class _CatalogViewState extends State<CatalogView> {
  int currentPage = 0; // Current page number

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.catalogTitle), // Use the passed title
        centerTitle: true,
      ),
      body: Column(
        children: [
          Expanded(
            child: PageView.builder(
              itemCount: widget.catalogImages.isNotEmpty ? widget.catalogImages.length : 1,
              onPageChanged: (index) {
                setState(() {
                  currentPage = index;
                });
              },
              itemBuilder: (context, index) {
                if (widget.catalogImages.isEmpty) {
                  return const Center(
                    child: Text(
                      'No catalog images available. Please check the data source.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 18),
                    ),
                  );
                }
                return Image.asset(
                  widget.catalogImages[index],
                  fit: BoxFit.contain,
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Text(
              widget.catalogImages.isNotEmpty
                  ? 'Page ${currentPage + 1} / ${widget.catalogImages.length}'
                  : 'Loading Catalog...',
              style: const TextStyle(fontSize: 16),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
            child: Text(
              'Validity: ${widget.catalogValidity}',
              style: const TextStyle(fontSize: 14, color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }
}