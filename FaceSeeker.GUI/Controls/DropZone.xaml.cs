// ponytail: clean reusable drag-drop control with dependency properties
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace FaceSeeker.GUI.Controls
{
    public partial class DropZone : UserControl
    {
        public static readonly DependencyProperty FilesDroppedProperty =
            DependencyProperty.Register(nameof(FilesDropped), typeof(ICommand), typeof(DropZone), new PropertyMetadata(null));

        public static readonly DependencyProperty AcceptedExtensionsProperty =
            DependencyProperty.Register(nameof(AcceptedExtensions), typeof(string), typeof(DropZone), new PropertyMetadata(""));

        public static readonly DependencyProperty LabelTextProperty =
            DependencyProperty.Register(nameof(LabelText), typeof(string), typeof(DropZone), new PropertyMetadata("Drop files here", (d, e) =>
            {
                if (d is DropZone dz) dz.LabelDisplay.Text = e.NewValue as string ?? "";
            }));

        public ICommand? FilesDropped
        {
            get => (ICommand?)GetValue(FilesDroppedProperty);
            set => SetValue(FilesDroppedProperty, value);
        }

        public string AcceptedExtensions
        {
            get => (string)GetValue(AcceptedExtensionsProperty);
            set => SetValue(AcceptedExtensionsProperty, value);
        }

        public string LabelText
        {
            get => (string)GetValue(LabelTextProperty);
            set => SetValue(LabelTextProperty, value);
        }

        public DropZone()
        {
            InitializeComponent();
        }

        private void OnDragEnter(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                e.Effects = DragDropEffects.Copy;
                ContainerBorder.BorderBrush = new SolidColorBrush(Color.FromRgb(0, 173, 181));
                ContainerBorder.Background = new SolidColorBrush(Color.FromArgb(40, 0, 173, 181));
            }
            else
            {
                e.Effects = DragDropEffects.None;
            }
            e.Handled = true;
        }

        private void OnDragLeave(object sender, DragEventArgs e)
        {
            ContainerBorder.BorderBrush = new SolidColorBrush(Color.FromRgb(48, 54, 61));
            ContainerBorder.Background = new SolidColorBrush(Color.FromRgb(22, 27, 34));
            e.Handled = true;
        }

        private void OnDrop(object sender, DragEventArgs e)
        {
            ContainerBorder.BorderBrush = new SolidColorBrush(Color.FromRgb(48, 54, 61));
            ContainerBorder.Background = new SolidColorBrush(Color.FromRgb(22, 27, 34));

            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                string[]? files = e.Data.GetData(DataFormats.FileDrop) as string[];
                if (files != null && files.Length > 0)
                {
                    var allowed = (AcceptedExtensions ?? "")
                        .Split(';', StringSplitOptions.RemoveEmptyEntries)
                        .Select(x => x.Trim().ToLowerInvariant())
                        .ToList();

                    var matched = new List<string>();
                    foreach (var file in files)
                    {
                        if (allowed.Count == 0)
                        {
                            matched.Add(file);
                        }
                        else
                        {
                            string ext = Path.GetExtension(file).ToLowerInvariant();
                            if (allowed.Contains(ext))
                            {
                                matched.Add(file);
                            }
                        }
                    }

                    if (matched.Count > 0 && FilesDropped != null)
                    {
                        if (FilesDropped.CanExecute(matched))
                        {
                            FilesDropped.Execute(matched);
                        }
                        else if (FilesDropped.CanExecute(matched.ToArray()))
                        {
                            FilesDropped.Execute(matched.ToArray());
                        }
                        else
                        {
                            foreach (var m in matched)
                            {
                                if (FilesDropped.CanExecute(m))
                                {
                                    FilesDropped.Execute(m);
                                }
                            }
                        }
                    }
                }
            }
            e.Handled = true;
        }
    }
}