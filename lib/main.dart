import 'package:flutter/material.dart';
import 'package:catalog_app/brochure_list_screen.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:catalog_app/firebase_options.dart'; 
import 'package:catalog_app/catalog_view.dart';

void main() async { 
  WidgetsFlutterBinding.ensureInitialized(); 
  await Firebase.initializeApp( 
    options: DefaultFirebaseOptions.currentPlatform,
  );
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