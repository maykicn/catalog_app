import 'package:cloud_firestore/cloud_firestore.dart';

class Brochure {
  final String id;
  final String marketName; // Yeni eklendi
  final String title;
  final String validity;
  final String thumbnailUrl;
  final List<String> catalogPageImages; // Alan adı düzeltildi
  final Timestamp timestamp; // Yeni eklendi

  Brochure({
    required this.id,
    required this.marketName,
    required this.title,
    required this.validity,
    required this.thumbnailUrl,
    required this.catalogPageImages,
    required this.timestamp,
  });

  // Firestore DocumentSnapshot'tan Brochure nesnesi oluşturmak için factory constructor
  factory Brochure.fromFirestore(DocumentSnapshot doc) {
    Map<String, dynamic> data = doc.data() as Map<String, dynamic>; // Veriyi Map'e dönüştür
    return Brochure(
      id: doc.id, // Doküman ID'si
      marketName: data['marketName'] ?? 'Bilinmeyen Market', // Firestore'dan marketName
      title: data['title'] ?? 'Bilinmeyen Başlık',
      validity: data['validity'] ?? 'Geçerlilik Yok',
      thumbnailUrl: data['thumbnailUrl'] ?? '',
      catalogPageImages: List<String>.from(data['catalogPageImages'] ?? []), // Firebase'deki 'catalogPageImages'
      timestamp: data['timestamp'] as Timestamp, // Firebase'deki 'timestamp'
    );
  }

  // Opsiyonel: Brochure nesnesini Firestore'a göndermek için (şimdilik kullanmayacağız)
  Map<String, dynamic> toFirestore() {
    return {
      'marketName': marketName,
      'title': title,
      'validity': validity,
      'thumbnailUrl': thumbnailUrl,
      'catalogPageImages': catalogPageImages,
      'timestamp': timestamp,
    };
  }
}