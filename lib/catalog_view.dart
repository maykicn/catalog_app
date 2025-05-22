import 'package:flutter/material.dart';
import 'package:catalog_app/models/brochure.dart'; // Brochure modelini import ediyoruz

class CatalogView extends StatefulWidget {
  final Brochure brochure; // Artık tek bir Brochure nesnesi alıyoruz

  const CatalogView({
    super.key,
    required this.brochure, // Constructor'ı güncelledik
  });

  @override
  State<CatalogView> createState() => _CatalogViewState();
}

class _CatalogViewState extends State<CatalogView> {
  late PageController _pageController; // Sayfalar arası geçiş için PageController
  int _currentPage = 0; // Mevcut sayfa numarası

  @override
  void initState() {
    super.initState();
    _pageController = PageController(); // PageController'ı başlat
  }

  @override
  void dispose() {
    _pageController.dispose(); // Controller'ı dispose etmeyi unutma
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        // Başlığı brochure nesnesinden alıyoruz
        title: Text(widget.brochure.title), 
        centerTitle: true,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(20.0), // Küçük bir alt bar yüksekliği
          child: Padding(
            padding: const EdgeInsets.only(bottom: 8.0),
            child: Text(
              // Geçerlilik tarihini brochure nesnesinden alıyoruz
              widget.brochure.validity, 
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
          ),
        ),
      ),
      body: PageView.builder(
        controller: _pageController,
        itemCount: widget.brochure.catalogPageImages.length, // Resim sayısı kadar sayfa
        itemBuilder: (context, index) {
          // Her sayfada katalog resmini göster
          return Center(
            child: InteractiveViewer( // Resimleri yakınlaştırma/kaydırma için
              maxScale: 4.0, // Maksimum yakınlaştırma
              minScale: 0.8, // Minimum yakınlaştırma (küçültme)
              child: Image.asset(
                widget.brochure.catalogPageImages[index], // Resim yolunu kullan
                fit: BoxFit.contain, // Resmi sayfaya sığdır
                errorBuilder: (context, error, stackTrace) {
                  return const Center(child: Text('Resim yüklenemedi.')); // Hata mesajı
                },
              ),
            ),
          );
        },
        onPageChanged: (int page) {
          setState(() {
            _currentPage = page; // Sayfa değiştikçe güncel sayfa numarasını ayarla
          });
        },
      ),
      bottomNavigationBar: BottomAppBar(
        color: Theme.of(context).appBarTheme.backgroundColor, // AppBar rengini kullan
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back_ios, color: Colors.white),
              onPressed: _currentPage > 0
                  ? () {
                      _pageController.previousPage(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.ease,
                      );
                    }
                  : null, // İlk sayfadaysa devre dışı
            ),
            Text(
              // Sayfa numarası gösterimi
              'Sayfa ${_currentPage + 1} / ${widget.brochure.catalogPageImages.length}',
              style: const TextStyle(color: Colors.white, fontSize: 16),
            ),
            IconButton(
              icon: const Icon(Icons.arrow_forward_ios, color: Colors.white),
              onPressed: _currentPage < widget.brochure.catalogPageImages.length - 1
                  ? () {
                      _pageController.nextPage(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.ease,
                      );
                    }
                  : null, // Son sayfadaysa devre dışı
            ),
          ],
        ),
      ),
    );
  }
}